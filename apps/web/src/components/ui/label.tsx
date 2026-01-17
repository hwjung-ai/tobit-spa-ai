import React from 'react';

export const Label = ({ children, ...rest }: { children?: React.ReactNode } & React.LabelHTMLAttributes<HTMLLabelElement>) => {
  return <label {...rest}>{children}</label>;
};
