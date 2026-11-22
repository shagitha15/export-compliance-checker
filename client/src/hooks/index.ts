// Custom React Hooks
export const useToggle = (initial = false) => {
  const [value, setValue] = React.useState(initial);
  const toggle = () => setValue((v) => !v);
  return [value, toggle] as const;
};
