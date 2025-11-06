import { Link } from "@tanstack/react-router";
import { Home, Menu, X } from "lucide-react";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { logoutMutation } from "@/client/@tanstack/react-query.gen";
import { readUsersMeOptions } from "@/client/@tanstack/react-query.gen";

export default function Header() {
  const [isOpen, setIsOpen] = useState(false);
  const logout = useMutation({
    ...logoutMutation(),
  });

  function onLogout() {
    logout.mutate();
    window.location.reload();
  }

  const { data } = useQuery({
    ...readUsersMeOptions({}),
  });
  return (
    <>
      <header className="p-4 w-full flex justify-between items-center bg-[#45474B] text-white shadow-lg">
        <div className="flex items-center justify-center">
          <button
            type="button"
            onClick={() => setIsOpen(true)}
            className="p-2 hover:bg-[#222222] rounded-lg transition-colors"
            aria-label="Open menu"
          >
            <Menu size={24} />
          </button>
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
            <Home size={20} />
            <span className="font-medium">Log out</span>
          </Link>
        ) : (
          <Link
            to="/signIn"
            className="flex items-center gap-3 p-3 rounded-lg hover:bg-[#333333] transition-colors"
          >
            <Home size={20} />
            <span className="font-medium">Log in</span>
          </Link>
        )}
      </header>

      <aside
        className={`fixed top-0 left-0 h-full w-80 bg-[#45474B] text-[#f5f7f8] shadow-2xl z-50 transform transition-transform duration-300 ease-in-out flex flex-col ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-xl font-bold">Navigation</h2>
          <button
            type="button"
            onClick={() => setIsOpen(false)}
            className="p-2 hover:bg-[#333333] rounded-lg transition-colors"
            aria-label="Close menu"
          >
            <X size={24} />
          </button>
        </div>

        <nav className="flex-1 p-4 overflow-y-auto">
          <Link
            to="/"
            onClick={() => setIsOpen(false)}
            className="flex items-center gap-3 p-3 rounded-lg hover:bg-[#333333] transition-colors mb-2"
            activeProps={{
              className:
                "flex items-center gap-3 p-3 text-[#45474B] rounded-lg bg-[#f5f7f8] hover:bg-[#dcdedf] transition-colors mb-2",
            }}
          >
            <Home size={20} />
            <span className="font-medium">Home</span>
          </Link>

          <Link
            to="/register"
            onClick={() => setIsOpen(false)}
            className="flex items-center gap-3 p-3 rounded-lg hover:bg-[#333333] transition-colors mb-2"
            activeProps={{
              className:
                "flex items-center gap-3 p-3 rounded-lg text-[#45474B] rounded-lg bg-[#f5f7f8] hover:bg-[#dcdedf] transition-colors mb-2",
            }}
          >
            <Home size={20} />
            <span className="font-medium">Register</span>
          </Link>
        </nav>
      </aside>
    </>
  );
}
