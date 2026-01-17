import React from 'react';

export const Button = React.forwardRef<HTMLButtonElement, React.ButtonHTMLAttributes<HTMLButtonElement>>((props, ref) => {
  const { children, className, ...rest } = props;
  return (
    <button ref={ref} className={className ?? ''} {...rest}>
      {children}
    </button>
  );
});
Button.displayName = 'Button';
