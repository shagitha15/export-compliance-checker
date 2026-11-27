import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  Bell,
  CheckCircle2,
  Clock,
  ExternalLink,
  GitCommit,
  Globe,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react';
import {
  GovernmentNotificationRecord,
  GovernmentRuleRecord,
  RuleSyncRunReport,
  RuleVersionHistoryEntry,
  RulesMonitoringOverview,
  rulesService,
} from '../../services/rulesService';

type MonitorTab = 'rules' | 'notifications' | 'versions';

function formatTimestamp(ts: string | null | undefined): string {
  if (!ts) return 'Not yet synced';
  const dt = new Date(ts);
  if (Number.isNaN(dt.getTime())) return ts;
  return dt.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function VerificationBadge({ status }: { status: string }) {
  const isVerified = status === 'verified' || status === 'success' || status === 'validated';
  const isReview = status === 'manual_review';
  const isWithdrawn = status === 'withdrawn' || status === 'tls_error' || status === 'network_error' || status === 'failed';

  const bg = isVerified
    ? 'rgba(13, 148, 136, 0.12)'
    : isReview
    ? 'rgba(69, 107, 139, 0.16)'
    : isWithdrawn
    ? 'rgba(30, 58, 95, 0.14)'
    : '#EAF2F8';
  const color = isVerified ? '#0D9488' : isWithdrawn ? '#102A43' : '#1E3A5F';
  const border = isVerified ? 'rgba(13, 148, 136, 0.35)' : '#9FBAD0';

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '5px',
        padding: '3px 9px',
        borderRadius: '999px',
        fontSize: '11px',
        fontWeight: 700,
        letterSpacing: '0.02em',
        textTransform: 'uppercase',
        backgroundColor: bg,
        color,
        border: `1px solid ${border}`,
        whiteSpace: 'nowrap',
      }}
    >
      {isVerified && <CheckCircle2 size={11} />}
      {isReview && <AlertTriangle size={11} />}
      {status.replace(/_/g, ' ')}
    </span>
  );
}

export const GovernmentRulesMonitorSection: React.FC = () => {
  const [overview, setOverview] = useState<RulesMonitoringOverview | null>(null);
  const [rules, setRules] = useState<GovernmentRuleRecord[]>([]);
  const [notifications, setNotifications] = useState<GovernmentNotificationRecord[]>([]);
  const [versions, setVersions] = useState<RuleVersionHistoryEntry[]>([]);
  const [activeTab, setActiveTab] = useState<MonitorTab>('rules');
  const [sourceFilter, setSourceFilter] = useState<string>('ALL');
  const [loading, setLoading] = useState<boolean>(true);
  const [syncing, setSyncing] = useState<boolean>(false);
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [syncBanner, setSyncBanner] = useState<RuleSyncRunReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [ov, ruleRows, notifRows, verRows] = await Promise.all([
        rulesService.getOverview(),
        rulesService.listRules(sourceFilter),
        rulesService.listNotifications(),
        rulesService.listVersions(),
      ]);
      setOverview(ov);
      setRules(ruleRows);
      setNotifications(notifRows);
      setVersions(verRows);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load government rules monitoring data.');
    } finally {
      setLoading(false);
    }
  }, [sourceFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleManualSync = async () => {
    setSyncing(true);
    setError(null);
    try {
      const report = await rulesService.syncNow();
      setSyncBanner(report);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Live government sync failed.');
    } finally {
      setSyncing(false);
    }
  };

  const handleApproveRule = async (ruleId: string) => {
    setApprovingId(ruleId);
    setError(null);
    try {
      await rulesService.approveRule(ruleId);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Rule approval failed.');
    } finally {
      setApprovingId(null);
    }
  };

  const statCards = [
    {
      label: 'Last Successful Sync',
      value: overview ? formatTimestamp(overview.last_successful_sync) : '—',
      sub: overview?.scheduler_enabled
        ? `Auto-sync every ${overview.scheduler_interval_hours}h`
        : 'Auto-sync disabled',
    },
    {
      label: 'Total Rules',
      value: overview ? String(overview.total_rules) : '—',
      sub: overview ? `${overview.active_rules} active · ${overview.manual_review_rules} manual review` : '',
    },
    {
      label: 'New Rules Detected',
      value: overview ? String(overview.new_rules_detected) : '—',
      sub: 'Latest sync cycle',
    },
    {
      label: 'Updated Rules',
      value: overview ? String(overview.updated_rules) : '—',
      sub: 'Versioned revisions',
    },
    {
      label: 'Withdrawn Rules',
      value: overview ? String(overview.withdrawn_rules) : '—',
      sub: 'Removed from vector index',
    },
    {
      label: 'Sync Status',
      value: overview ? overview.last_sync_status.replace(/_/g, ' ').toUpperCase() : '—',
      sub: overview ? `Store: ${overview.storage_backend === 'supabase' ? 'Supabase DB' : 'Local Registry'}` : '',
    },
  ];

  return (
    <section
      aria-label="Government Rules Monitoring"
      style={{
        marginTop: '24px',
        borderRadius: '14px',
        background: 'linear-gradient(135deg, #102A43 0%, #1E3A5F 52%, #456B8B 100%)',
        padding: '22px',
        color: '#FFFFFF',
        boxShadow: '0 10px 28px rgba(16, 42, 67, 0.16)',
      }}
    >
      {/* Header Row */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '14px',
          marginBottom: '18px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Globe size={18} color="#9FBAD0" />
            <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 700, color: '#FFFFFF' }}>
              Government Rules Monitoring
            </h3>
          </div>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#EAF2F8' }}>
            Live official regulatory synchronization from DGFT, CBIC, and ICEGATE with immutable version history.
          </p>
        </div>

        <button
          type="button"
          onClick={handleManualSync}
          disabled={syncing}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 18px',
            borderRadius: '8px',
            border: 'none',
            backgroundColor: '#0D9488',
            color: '#FFFFFF',
            fontSize: '13.5px',
            fontWeight: 700,
            cursor: syncing ? 'not-allowed' : 'pointer',
            opacity: syncing ? 0.8 : 1,
            boxShadow: '0 4px 12px rgba(13, 148, 136, 0.35)',
          }}
        >
          <RefreshCw size={15} className={syncing ? 'animate-spin' : ''} />
          {syncing ? 'Syncing Official Portals...' : 'Sync Government Rules'}
        </button>
      </div>

      {/* Live Sync Result / Error Banner */}
      {error && (
        <div
          style={{
            marginBottom: '16px',
            padding: '12px 14px',
            borderRadius: '8px',
            backgroundColor: '#EAF2F8',
            color: '#102A43',
            border: '1px solid #9FBAD0',
            fontSize: '13px',
            fontWeight: 600,
          }}
        >
          {error}
        </div>
      )}

      {syncBanner && (
        <div
          style={{
            marginBottom: '16px',
            padding: '12px 16px',
            borderRadius: '8px',
            backgroundColor: 'rgba(255, 255, 255, 0.96)',
            color: '#102A43',
            borderLeft: `4px solid ${syncBanner.overall_status === 'success' ? '#0D9488' : '#1E3A5F'}`,
            fontSize: '13px',
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: '4px' }}>
            Sync Complete ({syncBanner.overall_status.toUpperCase()}): {syncBanner.message}
          </div>
          <div style={{ fontSize: '12px', color: '#456B8B' }}>
            Fetched {syncBanner.notifications_fetched} notices · New: {syncBanner.new_rules_detected} · Updated:{' '}
            {syncBanner.updated_rules} · Manual Review: {syncBanner.manual_review_rules} · Pinecone Upserted:{' '}
            {syncBanner.pinecone_upserted}
          </div>
        </div>
      )}

      {/* KPI Metrics Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(175px, 1fr))',
          gap: '12px',
          marginBottom: '16px',
        }}
      >
        {statCards.map((card) => (
          <div
            key={card.label}
            style={{
              backgroundColor: '#FFFFFF',
              borderRadius: '10px',
              padding: '14px 16px',
              border: '1px solid #9FBAD0',
              color: '#102A43',
            }}
          >
            <div style={{ fontSize: '11.5px', fontWeight: 700, color: '#456B8B', textTransform: 'uppercase' }}>
              {card.label}
            </div>
            <div style={{ fontSize: '18px', fontWeight: 800, color: '#102A43', marginTop: '4px' }}>
              {card.value}
            </div>
            {card.sub && <div style={{ fontSize: '11.5px', color: '#456B8B', marginTop: '3px' }}>{card.sub}</div>}
          </div>
        ))}
      </div>

      {/* Government Sources Health Strip */}
      {overview && (
        <div
          style={{
            backgroundColor: '#EAF2F8',
            borderRadius: '10px',
            padding: '14px 16px',
            marginBottom: '16px',
            color: '#102A43',
          }}
        >
          <div style={{ fontSize: '12px', fontWeight: 700, color: '#1E3A5F', marginBottom: '10px', textTransform: 'uppercase' }}>
            Government Sources Monitored
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '10px' }}>
            {overview.government_sources.map((src) => (
              <div
                key={src.source}
                style={{
                  backgroundColor: '#FFFFFF',
                  border: '1px solid #9FBAD0',
                  borderRadius: '8px',
                  padding: '10px 12px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
                  <strong style={{ fontSize: '13px', color: '#102A43' }}>{src.source}</strong>
                  <VerificationBadge status={src.last_status} />
                </div>
                <div style={{ fontSize: '12px', color: '#456B8B', marginTop: '4px' }}>{src.label}</div>
                <div style={{ marginTop: '6px', display: 'flex', justifyContent: 'space-between', fontSize: '11px' }}>
                  <span style={{ color: '#456B8B' }}>
                    Checked: {src.last_checked_at ? formatTimestamp(src.last_checked_at) : 'Pending'}
                  </span>
                  <a
                    href={src.portal_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: '#1E3A5F', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '3px' }}
                  >
                    Portal <ExternalLink size={10} />
                  </a>
                </div>
                {src.last_error && (
                  <div style={{ marginTop: '6px', fontSize: '11px', color: '#102A43', backgroundColor: '#EAF2F8', padding: '5px 7px', borderRadius: '4px' }}>
                    {src.last_error}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* White Workspace Panel for Tables & Tabs */}
      <div
        style={{
          backgroundColor: '#FFFFFF',
          borderRadius: '12px',
          padding: '18px',
          color: '#102A43',
          border: '1px solid #9FBAD0',
        }}
      >
        {/* Tab Switcher + Source Filter */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '10px',
            marginBottom: '14px',
            borderBottom: '1px solid #EAF2F8',
            paddingBottom: '12px',
          }}
        >
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {[
              { id: 'rules' as const, label: `Active & Review Rules (${rules.length})`, icon: ShieldCheck },
              { id: 'notifications' as const, label: `Latest Notifications (${notifications.length})`, icon: Bell },
              { id: 'versions' as const, label: `Rule Version History (${versions.length})`, icon: GitCommit },
            ].map((tab) => {
              const Icon = tab.icon;
              const active = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '7px 13px',
                    borderRadius: '7px',
                    fontSize: '12.5px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    border: active ? '1px solid #102A43' : '1px solid #9FBAD0',
                    backgroundColor: active ? '#102A43' : '#EAF2F8',
                    color: active ? '#FFFFFF' : '#1E3A5F',
                  }}
                >
                  <Icon size={14} />
                  {tab.label}
                </button>
              );
            })}
          </div>

          {activeTab === 'rules' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '12px', fontWeight: 600, color: '#456B8B' }}>Source:</span>
              {['ALL', 'DGFT', 'CBIC', 'ICEGATE', 'RBI'].map((src) => (
                <button
                  key={src}
                  type="button"
                  onClick={() => setSourceFilter(src)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '6px',
                    fontSize: '11.5px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    border: '1px solid #9FBAD0',
                    backgroundColor: sourceFilter === src ? '#1E3A5F' : '#FFFFFF',
                    color: sourceFilter === src ? '#FFFFFF' : '#1E3A5F',
                  }}
                >
                  {src}
                </button>
              ))}
            </div>
          )}
        </div>

        {loading ? (
          <div style={{ padding: '24px', textAlign: 'center', color: '#456B8B', fontSize: '13px' }}>
            Loading regulatory registry...
          </div>
        ) : activeTab === 'rules' ? (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12.5px' }}>
              <thead>
                <tr style={{ backgroundColor: '#EAF2F8', color: '#102A43', textAlign: 'left' }}>
                  <th style={{ padding: '10px 10px' }}>Rule Name</th>
                  <th style={{ padding: '10px 10px' }}>Notification No.</th>
                  <th style={{ padding: '10px 10px' }}>Source</th>
                  <th style={{ padding: '10px 10px' }}>Published Date</th>
                  <th style={{ padding: '10px 10px' }}>Effective Date</th>
                  <th style={{ padding: '10px 10px' }}>Last Updated</th>
                  <th style={{ padding: '10px 10px' }}>Verification Status</th>
                  <th style={{ padding: '10px 10px' }}>Official Source</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((rule) => (
                  <tr key={rule.rule_id} style={{ borderBottom: '1px solid #EAF2F8' }}>
                    <td style={{ padding: '10px 10px', maxWidth: '300px' }}>
                      <div style={{ fontWeight: 700, color: '#102A43' }}>{rule.rule_title}</div>
                      <div style={{ fontSize: '11px', color: '#456B8B', marginTop: '2px' }}>
                        {rule.rule_id} · v{rule.version} · HS: {rule.applicable_hs_prefixes.join(', ')}
                      </div>
                      {rule.validation_notes.length > 0 && rule.verification_status === 'manual_review' && (
                        <div style={{ fontSize: '11px', color: '#1E3A5F', marginTop: '4px', backgroundColor: '#EAF2F8', padding: '4px 6px', borderRadius: '4px' }}>
                          Review note: {rule.validation_notes[0]}
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '10px 10px', fontWeight: 600, color: '#1E3A5F' }}>
                      {rule.notification_number}
                    </td>
                    <td style={{ padding: '10px 10px', fontWeight: 700, color: '#102A43' }}>{rule.source}</td>
                    <td style={{ padding: '10px 10px', color: '#456B8B' }}>{rule.published_date || '—'}</td>
                    <td style={{ padding: '10px 10px', color: '#456B8B' }}>{rule.effective_date || 'Not stated'}</td>
                    <td style={{ padding: '10px 10px', color: '#456B8B' }}>{formatTimestamp(rule.last_updated_at)}</td>
                    <td style={{ padding: '10px 10px' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', alignItems: 'flex-start' }}>
                        <VerificationBadge status={rule.verification_status} />
                        {rule.verification_status === 'manual_review' && (
                          <button
                            type="button"
                            onClick={() => handleApproveRule(rule.rule_id)}
                            disabled={approvingId === rule.rule_id}
                            style={{
                              padding: '3px 9px',
                              borderRadius: '5px',
                              border: 'none',
                              backgroundColor: '#0D9488',
                              color: '#FFFFFF',
                              fontSize: '11px',
                              fontWeight: 700,
                              cursor: 'pointer',
                            }}
                          >
                            {approvingId === rule.rule_id ? 'Approving...' : 'Approve & Index'}
                          </button>
                        )}
                      </div>
                    </td>
                    <td style={{ padding: '10px 10px' }}>
                      <a
                        href={rule.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          color: '#1E3A5F',
                          fontWeight: 600,
                          textDecoration: 'none',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                      >
                        Official Link <ExternalLink size={11} />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : activeTab === 'notifications' ? (
          notifications.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: '#456B8B', fontSize: '13px' }}>
              No live notifications fetched yet. Click <strong>Sync Government Rules</strong> above to fetch the latest notices.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {notifications.map((n) => (
                <div
                  key={n.notification_id}
                  style={{
                    border: '1px solid #9FBAD0',
                    borderRadius: '8px',
                    padding: '12px 14px',
                    backgroundColor: '#EAF2F8',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                    <div style={{ fontWeight: 700, color: '#102A43', fontSize: '13.5px' }}>
                      [{n.source}] {n.notification_number} — {n.title}
                    </div>
                    <VerificationBadge status={n.validation_status} />
                  </div>
                  <div style={{ fontSize: '12px', color: '#1E3A5F', marginTop: '5px' }}>{n.summary}</div>
                  <div
                    style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: '14px',
                      marginTop: '8px',
                      fontSize: '11.5px',
                      color: '#456B8B',
                    }}
                  >
                    <span>Category: {n.category}</span>
                    <span>Published: {n.published_date || '—'}</span>
                    <span>Effective: {n.effective_date || 'Not stated'}</span>
                    <a
                      href={n.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: '#102A43', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                    >
                      Official Source <ExternalLink size={11} />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {versions.length === 0 ? (
              <div style={{ padding: '24px', textAlign: 'center', color: '#456B8B', fontSize: '13px' }}>
                No rule version changes recorded yet.
              </div>
            ) : (
              versions.map((ver) => (
                <div
                  key={ver.version_id}
                  style={{
                    border: '1px solid #9FBAD0',
                    borderRadius: '8px',
                    padding: '11px 14px',
                    backgroundColor: '#FFFFFF',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '10px',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <span
                        style={{
                          padding: '2px 7px',
                          borderRadius: '4px',
                          backgroundColor: '#102A43',
                          color: '#FFFFFF',
                          fontSize: '11px',
                          fontWeight: 700,
                        }}
                      >
                        v{ver.version_number}
                      </span>
                      <strong style={{ fontSize: '13px', color: '#102A43' }}>{ver.rule_id}</strong>
                      <VerificationBadge status={ver.change_type} />
                    </div>
                    <div style={{ fontSize: '12.5px', color: '#1E3A5F', marginTop: '4px' }}>{ver.summary}</div>
                    <div style={{ fontSize: '11px', color: '#456B8B', marginTop: '3px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <Clock size={11} /> {formatTimestamp(ver.changed_at)}
                      </span>
                      <span>Source: {ver.source} ({ver.notification_number})</span>
                      {ver.effective_date && <span>Effective: {ver.effective_date}</span>}
                    </div>
                  </div>
                  <a
                    href={ver.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      color: '#1E3A5F',
                      fontWeight: 700,
                      fontSize: '12px',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    Source Notice <ExternalLink size={11} />
                  </a>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </section>
  );
};
