import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { getAllPollsOptions } from "@/client/@tanstack/react-query.gen";

export const Route = createFileRoute("/")({
  component: App,
});

function App() {
  const { data } = useQuery({
    ...getAllPollsOptions({}),
  });

  return <pre>{JSON.stringify(data, null, 2)}</pre>;
}
