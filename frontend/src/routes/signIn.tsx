import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { loginMutation } from "@/client/@tanstack/react-query.gen";
import { useMutation } from "@tanstack/react-query";
import { useEffect, useId, useState } from "react";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import InputPassword from "@/components/ui/password";

export const Route = createFileRoute("/signIn")({
  component: SignInComponent,
});
function SignInComponent() {
  const [status, setStatus] = useState("");
  const userLogin = useMutation({
    ...loginMutation(),
    onError: () => {
      setStatus("Login failed");
    },
    onSuccess: () => {
      setStatus("Login completed");
    },
  });
  const loginFormSchema = z.object({
    username: z.string().min(3, "Username must be at least 3 characters long"),
    password: z.string().min(8, "Password must be at least 8 characters long"),
  });
  const form = useForm<z.infer<typeof loginFormSchema>>({
    resolver: zodResolver(loginFormSchema),
    defaultValues: {
      username: "",
      password: "",
    },
  });
  const navigate = useNavigate();
  useEffect(() => {
    if (userLogin.isSuccess) {
      navigate({ to: "/" });
    }
  });

  function onSubmit(values: z.infer<typeof loginFormSchema>) {
    userLogin.mutate({
      body: {
        username: values.username,
        password: values.password,
      },
    });
    console.log(status);
  }

  return (
    <div>
      <div className="flex flex-col h-screen w-full items-center justify-center px-4">
        <Card className="mx-auto max-w-sm px-6 py-6">
          <CardHeader>
            <CardTitle className="text-2xl">Login</CardTitle>
            <CardDescription>
              Enter your username and password to login to your account.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="space-y-8"
              >
                <div className="grid gap-4">
                  <FormField
                    control={form.control}
                    name="username"
                    render={({ field }) => (
                      <FormItem className="grid gap-2">
                        <FormLabel htmlFor="email">Username</FormLabel>
                        <FormControl>
                          <Input
                            id={field.name}
                            placeholder="John Doe"
                            type="username"
                            autoComplete="username"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="password"
                    render={({ field }) => (
                      <FormItem className="grid gap-2">
                        <div className="flex justify-between items-center">
                          <FormLabel htmlFor="password">Password</FormLabel>
                          <Link
                            to="/register"
                            className="ml-auto inline-block text-sm underline"
                          >
                            Forgot your password?
                          </Link>
                        </div>
                        <FormControl>
                          <InputPassword
                            id={field.name}
                            placeholder="******"
                            autoComplete="current-password"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <Button type="submit" className="w-full">
                    Login
                  </Button>
                </div>
              </form>
            </Form>
            <div className="mt-4 text-center text-sm">
              Don&apos;t have an account?{" "}
              <Link to="/register" className="underline">
                Sign up
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
