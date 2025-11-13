import { Link } from "@tanstack/react-router";
import { LogIn, LogOut } from "lucide-react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { logoutMutation } from "@/client/@tanstack/react-query.gen";
import { readUsersMeOptions } from "@/client/@tanstack/react-query.gen";

export default function Header() {
  const logout = useMutation({
    ...logoutMutation(),
  });

  function onLogout() {
    logout.mutate({});
    window.location.reload();
  }

  const { data } = useQuery({
    ...readUsersMeOptions({}),
  });
  return (
    <header className="p-4 w-full flex justify-between items-center bg-[#45474B] text-white shadow-lg">
      <div className="flex items-center justify-center">
        <h1 className="ml-4 text-xl font-semibold">
          <Link to="/">
            <h2 className="font-arial font-semibold text-2xl color-[#f5f7f8]">
              Feed app
            </h2>
          </Link>
        </h1>
      </div>
      {data ? (
        <Link
          to="/"
          onClick={() => onLogout()}
          className="flex items-center gap-3 p-3 rounded-lg hover:bg-[#333333] transition-colors"
        >
          <LogOut size={20} />
          <span className="font-medium">Log out</span>
        </Link>
      ) : (
        <Link
          to="/signIn"
          className="flex items-center gap-3 p-3 rounded-lg hover:bg-[#333333] transition-colors"
        >
          <LogIn size={20} />
          <span className="font-medium">Log in</span>
        </Link>
      )}
    </header>
  );
}
