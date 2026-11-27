"""
Phase 2 Authentication, JWT Verification, Organization Isolation, RBAC, and Database/Storage Tests.
Uses httpx.AsyncClient + ASGITransport with Windows IOCP event loop for sandbox-safe ASGI execution.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from httpx import ASGITransport, AsyncClient
from supabase_auth.errors import AuthApiError

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from server.auth.dependencies import get_current_user
from server.auth.jwt_verifier import verify_supabase_jwt
from server.auth.models import AuthenticatedUser, OrgRole
from server.main import app
from server.storage.document_storage import DocumentStorageService, build_org_storage_path

ORG_1_ID = "11111111-1111-4111-8111-111111111111"
ORG_2_ID = "22222222-2222-4222-8222-222222222222"


def _run_async(coro):
    if sys.platform == "win32":
        import _overlapped

        class _InProcessProactorEventLoop(asyncio.ProactorEventLoop):
            def __init__(self) -> None:
                asyncio.BaseEventLoop.__init__(self)
                proactor = asyncio.IocpProactor()
                self._proactor = proactor
                self._selector = proactor
                self._self_reading_future = None
                self._accept_futures = {}
                self._wakeup_ov = _overlapped.Overlapped(0)
                proactor.set_loop(self)

            def _make_self_pipe(self) -> None:
                pass

            def _close_self_pipe(self) -> None:
                pass

            def _loop_self_reading(self, f=None) -> None:
                pass

            def _write_to_self(self) -> None:
                if self._proactor is not None and self._proactor._iocp is not None:
                    _overlapped.PostQueuedCompletionStatus(
                        self._proactor._iocp, 0, 0, self._wakeup_ov.address
                    )

        return asyncio.run(coro, loop_factory=_InProcessProactorEventLoop)
    return asyncio.run(coro)


class TestPhase2AuthRbacSecurity(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_unauthenticated_requests_rejected_401(self):
        """All protected endpoints must reject missing or invalid Bearer tokens with 401."""

        async def _check():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                protected = [
                    ("GET", "/api/v1/auth/me"),
                    ("POST", "/api/v1/auth/logout"),
                    ("GET", "/api/v1/orgs"),
                    ("GET", "/api/v1/audits"),
                    ("POST", "/api/v1/compliance/validate"),
                    ("POST", "/api/v1/agent/analyze"),
                    ("POST", "/api/v1/fraud/inspect"),
                ]
                for method, path in protected:
                    resp = await client.request(method, path)
                    self.assertEqual(resp.status_code, 401, f"{method} {path} returned {resp.status_code}")

                bad_resp = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
                self.assertEqual(bad_resp.status_code, 401)

        _run_async(_check())

    def test_real_es256_jwt_verification_and_tamper_rejection(self):
        """Validates real ES256 signed JWTs via JWKS and rejects forged/wrong-aud tokens."""
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        now = int(time.time())

        valid_token = jwt.encode(
            {
                "sub": "user-uuid-123",
                "email": "officer@exporter.com",
                "aud": "authenticated",
                "exp": now + 600,
                "user_metadata": {"full_name": "Priya Nair"},
            },
            private_key,
            algorithm="ES256",
            headers={"kid": "test-es256-kid"},
        )

        mock_jwks = MagicMock()
        mock_jwks.get_signing_key_from_jwt.return_value = SimpleNamespace(key=public_key)

        mock_supa = MagicMock()
        mock_supa.auth.get_user.return_value = SimpleNamespace(
            user=SimpleNamespace(
                id="user-uuid-123",
                email="officer@exporter.com",
                user_metadata={"full_name": "Priya Nair"},
            )
        )

        with patch("server.auth.jwt_verifier._get_jwks_client", return_value=mock_jwks), patch(
            "server.auth.jwt_verifier.get_supabase_client", return_value=mock_supa
        ):
            principal = verify_supabase_jwt(valid_token)
            self.assertEqual(principal.user_id, "user-uuid-123")
            self.assertEqual(principal.email, "officer@exporter.com")
            self.assertEqual(principal.full_name, "Priya Nair")

            other_key = ec.generate_private_key(ec.SECP256R1())
            forged_token = jwt.encode(
                {"sub": "user-uuid-123", "aud": "authenticated", "exp": now + 600},
                other_key,
                algorithm="ES256",
            )
            with self.assertRaises(Exception) as ctx:
                verify_supabase_jwt(forged_token)
            self.assertEqual(getattr(ctx.exception, "status_code", None), 401)

    def test_cross_organization_isolation_returns_403(self):
        """User belonging only to Org 1 must be blocked (403) from accessing Org 2 audits/members."""
        user_a = AuthenticatedUser(user_id="user-a", email="a@org1.com")
        app.dependency_overrides[get_current_user] = lambda: user_a

        org1_membership = [
            {
                "organization_id": ORG_1_ID,
                "user_id": "user-a",
                "role": OrgRole.ADMIN.value,
                "status": "active",
                "organization": {"id": ORG_1_ID, "name": "Org One Exports"},
            }
        ]

        async def _check():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                with patch(
                    "server.auth.dependencies.get_settings",
                    return_value=SimpleNamespace(SINGLE_USER_MODE=False),
                ), patch(
                    "server.auth.dependencies.OrganizationRepository.list_user_organizations",
                    return_value=org1_membership,
                ):
                    r_forbidden_audits = await client.get("/api/v1/audits", headers={"X-Organization-ID": ORG_2_ID})
                    self.assertEqual(r_forbidden_audits.status_code, 403)

                    r_forbidden_members = await client.get(
                        f"/api/v1/orgs/{ORG_2_ID}/members",
                        headers={"X-Organization-ID": ORG_2_ID},
                    )
                    self.assertEqual(r_forbidden_members.status_code, 403)

                    r_forbidden_validate = await client.post(
                        "/api/v1/compliance/validate",
                        headers={"X-Organization-ID": ORG_2_ID},
                        json={"documents": {"Commercial Invoice": {"invoice_number": "INV-1"}}},
                    )
                    self.assertEqual(r_forbidden_validate.status_code, 403)

        _run_async(_check())

    def test_rbac_roles_enforced_viewer_vs_writer_vs_admin(self):
        """Viewer is read-only (403 on uploads/agent/member invites); CHA/Officer cannot manage members."""
        viewer_user = AuthenticatedUser(user_id="user-v", email="viewer@org1.com")
        app.dependency_overrides[get_current_user] = lambda: viewer_user

        viewer_membership = [
            {
                "organization_id": ORG_1_ID,
                "user_id": "user-v",
                "role": OrgRole.VIEWER.value,
                "status": "active",
                "organization": {"id": ORG_1_ID, "name": "Org One Exports"},
            }
        ]

        cha_membership = [
            {
                "organization_id": ORG_1_ID,
                "user_id": "user-v",
                "role": OrgRole.CHA_BROKER.value,
                "status": "active",
                "organization": {"id": ORG_1_ID, "name": "Org One Exports"},
            }
        ]

        async def _check():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                with patch(
                    "server.auth.dependencies.get_settings",
                    return_value=SimpleNamespace(SINGLE_USER_MODE=False),
                ), patch(
                    "server.auth.dependencies.OrganizationRepository.list_user_organizations",
                    return_value=viewer_membership,
                ), patch(
                    "server.routes.v1.audits.AuditRepository.list_batches",
                    return_value=[],
                ):
                    self.assertEqual((await client.get("/api/v1/audits")).status_code, 200)
                    self.assertEqual(
                        (
                            await client.post(
                                "/api/v1/compliance/validate",
                                json={"documents": {"Commercial Invoice": {"invoice_number": "INV-1"}}},
                            )
                        ).status_code,
                        200,
                    )
                    self.assertEqual(
                        (
                            await client.post("/api/v1/agent/analyze", json={"documents": {"Commercial Invoice": {}}})
                        ).status_code,
                        403,
                    )
                    self.assertEqual(
                        (
                            await client.post(
                                f"/api/v1/orgs/{ORG_1_ID}/members",
                                json={"email": "new@org1.com", "role": "Viewer"},
                            )
                        ).status_code,
                        403,
                    )

                with patch(
                    "server.auth.dependencies.get_settings",
                    return_value=SimpleNamespace(SINGLE_USER_MODE=False),
                ), patch(
                    "server.auth.dependencies.OrganizationRepository.list_user_organizations",
                    return_value=cha_membership,
                ):
                    self.assertEqual(
                        (
                            await client.post(
                                f"/api/v1/orgs/{ORG_1_ID}/members",
                                json={"email": "new@org1.com", "role": "Viewer"},
                            )
                        ).status_code,
                        403,
                    )

        _run_async(_check())

    def test_private_storage_path_isolation_and_sql_migration_present(self):
        """Storage path traversal and cross-org paths must be rejected; SQL migration covers all tables & RLS."""
        path = build_org_storage_path(ORG_1_ID, "batch_abc", "../../secret.pdf")
        self.assertTrue(path.startswith(f"{ORG_1_ID}/batch_abc/secret.pdf"))
        self.assertNotIn("..", path)

        svc = DocumentStorageService()
        with self.assertRaises(PermissionError):
            svc.create_signed_download_url(ORG_1_ID, f"{ORG_2_ID}/batch_abc/invoice.pdf")
        with self.assertRaises(PermissionError):
            svc.download_private_pdf(ORG_1_ID, f"{ORG_2_ID}/batch_abc/invoice.pdf")

        sql_path = Path(WORKSPACE_ROOT) / "supabase" / "migrations" / "20261125000001_phase2_enterprise_schema.sql"
        self.assertTrue(sql_path.is_file())
        sql_text = sql_path.read_text(encoding="utf-8")
        for required_token in (
            "CREATE TABLE IF NOT EXISTS public.organizations",
            "CREATE TABLE IF NOT EXISTS public.organization_memberships",
            "CREATE TABLE IF NOT EXISTS public.audit_batches",
            "CREATE TABLE IF NOT EXISTS public.batch_documents",
            "CREATE TABLE IF NOT EXISTS public.audit_findings",
            "CREATE TABLE IF NOT EXISTS public.compliance_reports",
            "ENABLE ROW LEVEL SECURITY",
            "user_has_org_role",
        ):
            self.assertIn(required_token, sql_text)

    def test_login_email_not_confirmed_returns_clear_403(self):
        """Unconfirmed email login error must return structured 403 error_code instead of generic invalid password."""

        async def _check():
            mock_auth_client = MagicMock()
            mock_auth_client.auth.sign_in_with_password.side_effect = AuthApiError(
                "Email not confirmed", status=400, code="email_not_confirmed"
            )
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                with patch("server.routes.v1.auth.create_ephemeral_supabase_client", return_value=mock_auth_client):
                    resp = await client.post(
                        "/api/v1/auth/login",
                        json={"email": "pending@company.com", "password": "Password123!"},
                    )
                    self.assertEqual(resp.status_code, 403)
                    body = resp.json()
                    self.assertEqual(body["error_code"], "email_not_confirmed")
                    self.assertIn("not been confirmed", body["detail"].lower())
                    self.assertEqual(resp.headers.get("X-Auth-Error-Code"), "email_not_confirmed")

        _run_async(_check())

    def test_login_invalid_credentials_and_success_preserved(self):
        """Invalid credentials still return 401 and valid logins still issue JWT session payloads."""

        async def _check():
            mock_bad_client = MagicMock()
            mock_bad_client.auth.sign_in_with_password.side_effect = AuthApiError(
                "Invalid login credentials", status=400, code="invalid_credentials"
            )
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                with patch("server.routes.v1.auth.create_ephemeral_supabase_client", return_value=mock_bad_client):
                    bad_resp = await client.post(
                        "/api/v1/auth/login",
                        json={"email": "user@company.com", "password": "WrongPassword"},
                    )
                    self.assertEqual(bad_resp.status_code, 401)
                    self.assertIn("Invalid email or password", bad_resp.json()["detail"])

                mock_good_client = MagicMock()
                mock_good_client.auth.sign_in_with_password.return_value = SimpleNamespace(
                    session=SimpleNamespace(
                        access_token="jwt.access.token",
                        refresh_token="refresh-tok-123",
                        expires_in=3600,
                    ),
                    user=SimpleNamespace(
                        id="user-123",
                        email="user@company.com",
                        user_metadata={"full_name": "Confirmed User"},
                    ),
                )
                with patch("server.routes.v1.auth.create_ephemeral_supabase_client", return_value=mock_good_client), patch(
                    "server.routes.v1.auth._load_org_list", return_value=([], True)
                ):
                    ok_resp = await client.post(
                        "/api/v1/auth/login",
                        json={"email": "user@company.com", "password": "Password123!"},
                    )
                    self.assertEqual(ok_resp.status_code, 200)
                    data = ok_resp.json()
                    self.assertEqual(data["access_token"], "jwt.access.token")
                    self.assertEqual(data["user"]["email"], "user@company.com")

        _run_async(_check())

    def test_resend_confirmation_email_success_and_errors(self):
        """Resend confirmation calls Supabase auth.resend(signup) and maps rate-limit/error responses clearly."""

        async def _check():
            mock_auth_client = MagicMock()
            mock_auth_client.auth.resend.return_value = SimpleNamespace(message_id="msg-1")
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                with patch("server.routes.v1.auth.create_ephemeral_supabase_client", return_value=mock_auth_client):
                    ok_resp = await client.post(
                        "/api/v1/auth/resend-confirmation",
                        json={"email": " pending@company.com "},
                    )
                    self.assertEqual(ok_resp.status_code, 200)
                    self.assertTrue(ok_resp.json()["success"])
                    self.assertIn("pending@company.com", ok_resp.json()["message"])
                    mock_auth_client.auth.resend.assert_called_once_with(
                        {"type": "signup", "email": "pending@company.com"}
                    )

                mock_rate_client = MagicMock()
                mock_rate_client.auth.resend.side_effect = AuthApiError(
                    "For security purposes, you can only request this after 60 seconds.",
                    status=429,
                    code="over_email_send_rate_limit",
                )
                with patch("server.routes.v1.auth.create_ephemeral_supabase_client", return_value=mock_rate_client):
                    rate_resp = await client.post(
                        "/api/v1/auth/resend-confirmation",
                        json={"email": "pending@company.com"},
                    )
                    self.assertEqual(rate_resp.status_code, 429)
                    self.assertIn("wait", rate_resp.json()["detail"].lower())

                mock_err_client = MagicMock()
                mock_err_client.auth.resend.side_effect = AuthApiError(
                    "Unable to validate email address: invalid format",
                    status=400,
                    code="validation_failed",
                )
                with patch("server.routes.v1.auth.create_ephemeral_supabase_client", return_value=mock_err_client):
                    err_resp = await client.post(
                        "/api/v1/auth/resend-confirmation",
                        json={"email": "bad-email"},
                    )
                    self.assertEqual(err_resp.status_code, 400)
                    self.assertIn("Failed to resend confirmation email", err_resp.json()["detail"])

        _run_async(_check())

    def test_single_user_mode_enforces_jwt_and_bypasses_workflow_org_rbac_only(self):
        """SINGLE_USER_MODE keeps JWT auth active, bypasses workflow org/RBAC, and leaves /orgs & /audits strict."""
        from server.repositories.organization_repository import SchemaMigrationRequiredError

        single_user = AuthenticatedUser(user_id="single-user-1", email="solo@exporter.com")

        async def _check():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                with patch(
                    "server.auth.dependencies.get_settings",
                    return_value=SimpleNamespace(SINGLE_USER_MODE=True),
                ), patch(
                    "server.routes.v1.auth.get_settings",
                    return_value=SimpleNamespace(SINGLE_USER_MODE=True),
                ):
                    # 1. Unauthenticated requests MUST still be rejected with 401
                    app.dependency_overrides.clear()
                    self.assertEqual(
                        (
                            await client.post(
                                "/api/v1/compliance/validate",
                                json={"documents": {"Commercial Invoice": {"invoice_number": "INV-1"}}},
                            )
                        ).status_code,
                        401,
                    )
                    self.assertEqual(
                        (
                            await client.post("/api/v1/agent/analyze", json={"documents": {"Commercial Invoice": {}}})
                        ).status_code,
                        401,
                    )

                    # 2. Authenticated user without Phase 2 org tables can execute document workflow
                    app.dependency_overrides[get_current_user] = lambda: single_user
                    with patch(
                        "server.auth.dependencies.OrganizationRepository.list_user_organizations",
                        side_effect=SchemaMigrationRequiredError("Phase 2 tables not applied"),
                    ), patch(
                        "server.routes.v1.auth.OrganizationRepository.list_user_organizations",
                        side_effect=SchemaMigrationRequiredError("Phase 2 tables not applied"),
                    ):
                        me_resp = await client.get("/api/v1/auth/me")
                        self.assertEqual(me_resp.status_code, 200)
                        self.assertTrue(me_resp.json()["single_user_mode"])
                        self.assertFalse(me_resp.json()["schema_ready"])

                        val_resp = await client.post(
                            "/api/v1/compliance/validate",
                            json={"documents": {"Commercial Invoice": {"invoice_number": "INV-1"}}},
                        )
                        self.assertEqual(val_resp.status_code, 200)

                        fraud_resp = await client.post(
                            "/api/v1/fraud/inspect",
                            json={"documents": {"Commercial Invoice": {"invoice_number": "INV-1"}}},
                        )
                        self.assertEqual(fraud_resp.status_code, 200)

                        pdf_resp = await client.post(
                            "/api/v1/compliance/report/pdf",
                            json={
                                "batch_id": "single_batch_1",
                                "extracted_documents": {"Commercial Invoice": {"invoice_number": "INV-1"}},
                            },
                        )
                        self.assertEqual(pdf_resp.status_code, 200)
                        self.assertTrue(pdf_resp.content.startswith(b"%PDF"))

                        # Empty batch upload reaches controller validation (400) rather than org blocker (403/503)
                        batch_resp = await client.post("/api/v1/documents/batch-upload")
                        self.assertNotIn(batch_resp.status_code, (401, 403, 503))

                        # Agent workflow reaches AgentController (mocked to avoid external calls)
                        from server.schemas.agent import AgentAnalysisResponse, AgentSummary

                        mock_agent_resp = AgentAnalysisResponse(
                            execution_id="exec_single_1",
                            shipment_id="ship_single_1",
                            overall_compliance_status="APPROVED_FOR_EXPORT",
                            compliance_score=100.0,
                            critical_fraud_flag=False,
                            summary=AgentSummary(
                                documents_evaluated=1,
                                missing_documents=[],
                                passed_checks=1,
                                failed_checks=0,
                                statutory_compliant=True,
                                fraud_risk_level="GENUINE",
                                authenticity_score=100.0,
                            ),
                        )
                        with patch(
                            "server.routes.v1.agent.AgentController.analyze_shipment",
                            return_value=mock_agent_resp,
                        ):
                            agent_resp = await client.post(
                                "/api/v1/agent/analyze",
                                json={"documents": {"Commercial Invoice": {"invoice_number": "INV-1"}}},
                            )
                            self.assertEqual(agent_resp.status_code, 200)

                        # 3. Multi-tenant /orgs and /audits remain strictly protected (503 when schema missing)
                        self.assertEqual((await client.get("/api/v1/orgs")).status_code, 503)
                        self.assertEqual((await client.get("/api/v1/audits")).status_code, 503)

                # 4. Disabling SINGLE_USER_MODE restores strict org/RBAC checks on all workflow routes
                with patch(
                    "server.auth.dependencies.get_settings",
                    return_value=SimpleNamespace(SINGLE_USER_MODE=False),
                ), patch(
                    "server.auth.dependencies.OrganizationRepository.list_user_organizations",
                    return_value=[],
                ):
                    app.dependency_overrides[get_current_user] = lambda: single_user
                    self.assertEqual(
                        (
                            await client.post(
                                "/api/v1/compliance/validate",
                                json={"documents": {"Commercial Invoice": {"invoice_number": "INV-1"}}},
                            )
                        ).status_code,
                        403,
                    )
                    self.assertEqual(
                        (
                            await client.post("/api/v1/agent/analyze", json={"documents": {"Commercial Invoice": {}}})
                        ).status_code,
                        403,
                    )
                    self.assertEqual((await client.post("/api/v1/documents/batch-upload")).status_code, 403)

        _run_async(_check())

    def test_expired_jwt_rejected_401_and_refresh_enables_pdf_download(self):
        """Expired JWT on PDF route must return 401 token_expired; /auth/refresh issues valid JWT enabling PDF download."""
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        now = int(time.time())

        expired_jwt = jwt.encode(
            {
                "sub": "user-pdf-1",
                "email": "pdf@exporter.com",
                "aud": "authenticated",
                "exp": now - 120,
                "user_metadata": {"full_name": "PDF Exporter"},
            },
            private_key,
            algorithm="ES256",
            headers={"kid": "test-es256-kid"},
        )
        fresh_jwt = jwt.encode(
            {
                "sub": "user-pdf-1",
                "email": "pdf@exporter.com",
                "aud": "authenticated",
                "exp": now + 600,
                "user_metadata": {"full_name": "PDF Exporter"},
            },
            private_key,
            algorithm="ES256",
            headers={"kid": "test-es256-kid"},
        )

        mock_jwks = MagicMock()
        mock_jwks.get_signing_key_from_jwt.return_value = SimpleNamespace(key=public_key)

        mock_supa_service = MagicMock()
        mock_supa_service.auth.get_user.return_value = SimpleNamespace(
            user=SimpleNamespace(
                id="user-pdf-1",
                email="pdf@exporter.com",
                user_metadata={"full_name": "PDF Exporter"},
            )
        )

        mock_ephemeral_auth = MagicMock()
        mock_ephemeral_auth.auth.refresh_session.return_value = SimpleNamespace(
            session=SimpleNamespace(
                access_token=fresh_jwt,
                refresh_token="rotated-refresh-tok",
                expires_in=3600,
            ),
            user=SimpleNamespace(
                id="user-pdf-1",
                email="pdf@exporter.com",
                user_metadata={"full_name": "PDF Exporter"},
            ),
        )

        pdf_payload = {
            "batch_id": "batch_jwt_refresh_test",
            "extracted_documents": {"Commercial Invoice": {"invoice_number": "INV-900"}},
        }

        async def _check():
            app.dependency_overrides.clear()
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                with patch("server.auth.jwt_verifier._get_jwks_client", return_value=mock_jwks), patch(
                    "server.auth.jwt_verifier.get_supabase_client", return_value=mock_supa_service
                ), patch(
                    "server.auth.dependencies.get_settings",
                    return_value=SimpleNamespace(SINGLE_USER_MODE=True),
                ), patch(
                    "server.routes.v1.auth.get_settings",
                    return_value=SimpleNamespace(SINGLE_USER_MODE=True),
                ), patch(
                    "server.routes.v1.auth.create_ephemeral_supabase_client",
                    return_value=mock_ephemeral_auth,
                ), patch(
                    "server.routes.v1.auth._load_org_list",
                    return_value=([], False),
                ):
                    # 1. Expired JWT must fail signature/expiry verification with 401 token_expired
                    expired_resp = await client.post(
                        "/api/v1/compliance/report/pdf",
                        headers={"Authorization": f"Bearer {expired_jwt}"},
                        json=pdf_payload,
                    )
                    self.assertEqual(expired_resp.status_code, 401)
                    self.assertIn("Signature has expired", expired_resp.json()["detail"])
                    self.assertEqual(expired_resp.headers.get("X-Auth-Error-Code"), "token_expired")

                    # 2. Refresh token endpoint issues a fresh, valid JWT
                    refresh_resp = await client.post(
                        "/api/v1/auth/refresh",
                        json={"refresh_token": "initial-refresh-tok"},
                    )
                    self.assertEqual(refresh_resp.status_code, 200)
                    refresh_data = refresh_resp.json()
                    self.assertEqual(refresh_data["access_token"], fresh_jwt)
                    self.assertEqual(refresh_data["refresh_token"], "rotated-refresh-tok")

                    # 3. Retrying PDF download with refreshed JWT succeeds and streams valid PDF bytes
                    pdf_resp = await client.post(
                        "/api/v1/compliance/report/pdf",
                        headers={"Authorization": f"Bearer {refresh_data['access_token']}"},
                        json=pdf_payload,
                    )
                    self.assertEqual(pdf_resp.status_code, 200)
                    self.assertEqual(pdf_resp.headers.get("content-type"), "application/pdf")
                    self.assertTrue(pdf_resp.content.startswith(b"%PDF"))

                    # 4. Expired/revoked refresh token returns 401 refresh_failed
                    mock_ephemeral_auth.auth.refresh_session.side_effect = AuthApiError(
                        "Invalid Refresh Token: Already Used", status=400, code="refresh_token_already_used"
                    )
                    bad_refresh = await client.post(
                        "/api/v1/auth/refresh",
                        json={"refresh_token": "stale-tok"},
                    )
                    self.assertEqual(bad_refresh.status_code, 401)
                    self.assertEqual(bad_refresh.headers.get("X-Auth-Error-Code"), "refresh_failed")

        _run_async(_check())


if __name__ == "__main__":
    unittest.main()
