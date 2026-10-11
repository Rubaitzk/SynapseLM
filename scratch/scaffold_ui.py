import os

BASE_DIR = r"D:\Hackathons\SynapseLM\frontend\src\components"
UI_DIR = os.path.join(BASE_DIR, "ui")

os.makedirs(UI_DIR, exist_ok=True)

BUTTON_TSX = """import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
}

export function Button({ variant = 'primary', size = 'md', className = '', children, ...props }: ButtonProps) {
  const baseStyle = "inline-flex items-center justify-center font-medium rounded transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none";
  
  const variants = {
    primary: "bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500",
    secondary: "bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 focus:ring-gray-200",
    danger: "bg-red-600 text-white hover:bg-red-700 focus:ring-red-500",
    ghost: "text-gray-700 hover:bg-gray-100 focus:ring-gray-200"
  };

  const sizes = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-4 py-2",
    lg: "px-6 py-3 text-lg"
  };

  return (
    <button className={`${baseStyle} ${variants[variant]} ${sizes[size]} ${className}`} {...props}>
      {children}
    </button>
  );
}
"""

INPUT_TSX = """import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className = '', label, error, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>}
        <input
          ref={ref}
          className={`w-full px-3 py-2 border rounded shadow-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-colors ${
            error ? 'border-red-500' : 'border-gray-300'
          } ${className}`}
          {...props}
        />
        {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';
"""

CARD_TSX = """import React from 'react';

export function Card({ className = '', children }: { className?: string, children: React.ReactNode }) {
  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden ${className}`}>
      {children}
    </div>
  );
}

export function CardHeader({ className = '', children }: { className?: string, children: React.ReactNode }) {
  return <div className={`px-6 py-4 border-b border-gray-100 ${className}`}>{children}</div>;
}

export function CardBody({ className = '', children }: { className?: string, children: React.ReactNode }) {
  return <div className={`px-6 py-4 ${className}`}>{children}</div>;
}

export function CardFooter({ className = '', children }: { className?: string, children: React.ReactNode }) {
  return <div className={`px-6 py-4 bg-gray-50 border-t border-gray-100 ${className}`}>{children}</div>;
}
"""

with open(os.path.join(UI_DIR, "Button.tsx"), "w") as f:
    f.write(BUTTON_TSX)

with open(os.path.join(UI_DIR, "Input.tsx"), "w") as f:
    f.write(INPUT_TSX)

with open(os.path.join(UI_DIR, "Card.tsx"), "w") as f:
    f.write(CARD_TSX)

print("Created basic UI components")
