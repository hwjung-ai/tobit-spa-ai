import React from 'react';

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>((props, ref) => {
  const { ...rest } = props;
  return <input ref={ref} {...rest} />;
});
Input.displayName = 'Input';
