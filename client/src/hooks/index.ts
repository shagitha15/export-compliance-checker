import { useState } from 'react';

// Custom React Hooks
export const useToggle = (initial = false) => {
  const [value, setValue] = useState(initial);
  const toggle = () => setValue((v) => !v);
  return [value, toggle] as const;
};
