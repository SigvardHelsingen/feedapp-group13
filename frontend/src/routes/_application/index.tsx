import { useQuery } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { getAllPollsOptions } from "@/client/@tanstack/react-query.gen";

export const Route = createFileRoute("/_application/")({
  component: App,
});

function App() {
  const { data = [] } = useQuery({
    ...getAllPollsOptions({}),
  });
  const navigate = useNavigate();
  function handlePoll(id: number) {
    const path = `/poll/${encodeURIComponent(String(id))}`;
    navigate({ to: path });
  }
  return (
    <div className="">
      <ul
        role="list"
        className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 m-4"
      >
        {data.map((poll) => (
          <li
            key={poll.id}
            onClick={() => handlePoll(poll.id)}
            className="col-span-1 divide-y rounded-lg bg-white shadow dark:divide-white/10"
          >
            <div className="flex w-full items-center justify-between space-x-6 p-6">
              <div className="flex-1 truncate">
                <div className="flex items-center space-x-3">
                  <h3 className="truncate text-sm font-medium text-gray-900">
                    {poll.creator_name}
                  </h3>
                </div>
                <p className="mt-1 truncate text-sm text-gray-500">
                  {poll.question}
                </p>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
