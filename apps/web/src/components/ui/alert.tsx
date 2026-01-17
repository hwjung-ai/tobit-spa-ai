import React from 'react';

export const Alert = ({ children, ...rest }: { children?: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => {
  return (
    <div role="alert" {...rest}>
      {children}
    </div>
  );
};

export const AlertDescription = ({ children, ...rest }: { children?: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => {
  return <div {...rest}>{children}</div>;
};
