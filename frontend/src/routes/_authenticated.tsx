import Header from "@/components/Header";
import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated")({
  beforeLoad: async () => {
    return (
      <>
        <Header />
        <Outlet />
      </>
    );
  },
});
