import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/_application/_authenticated/createPoll")(
  {
    component: PollComponent,
  },
);

function PollComponent() {
  return <div>Hello "/_application/_authenticated/createPoll"!</div>;
}
