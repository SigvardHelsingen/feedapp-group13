"use client";

import { useId, useState } from "react";
import { EyeIcon, EyeOffIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

import type { InputHTMLAttributes } from "react";

type InputPasswordProps = InputHTMLAttributes<HTMLInputElement>;

const InputPassword = ({ id, ...props }: InputPasswordProps) => {
  const [isVisible, setIsVisible] = useState(false);
  const generatedId = useId();

  return (
    <div className="w-full max-w-xs space-y-2">
      <div className="relative">
        <Input
          id={id ?? generatedId}
          type={isVisible ? "text" : "password"}
          className="pr-9"
          {...props}
        />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          tabIndex={-1}
          onClick={() => setIsVisible((prevState) => !prevState)}
          className="text-muted-foreground focus-visible:ring-ring/50 absolute inset-y-0 right-0 rounded-l-none hover:bg-transparent"
        >
          {isVisible ? <EyeOffIcon /> : <EyeIcon />}
          <span className="sr-only">
            {isVisible ? "Hide password" : "Show password"}
          </span>
        </Button>
      </div>
    </div>
  );
};

export default InputPassword;
