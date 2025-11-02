import { createFileRoute } from "@tanstack/react-router";
import {
  getPollByIdOptions,
  submitVoteMutation,
} from "@/client/@tanstack/react-query.gen";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useState } from "react";

export const Route = createFileRoute(
  "/_application/_authenticated/poll/$pollId",
)({
  component: PollComponent,
});

function PollComponent() {
  const { pollId } = Route.useParams();

  const { data: selectedPoll, error } = useQuery({
    ...getPollByIdOptions({
      path: {
        poll_id: parseInt(pollId, 10),
      },
    }),
    retry: false,
  });

  const [status, setStatus] = useState("");
  const submitVote = useMutation({
    ...submitVoteMutation(),
    onError: () => {
      setStatus("Registration failed");
    },
    onSuccess: () => {
      setStatus("Registration completed");
    },
  });

  console.log(status);
  const [voteOptionId, setVoteOptionId] = useState(Number);
  function onSubmitVote() {
    submitVote.mutate({
      body: {
        poll_id: parseInt(pollId, 10),
        vote_option_id: voteOptionId,
      },
    });
  }
  return (
    <div className="p-6 h-screen max-w-6xl mx-auto">
      <div className="flex flex-col md:flex-row gap-6 justify-center items-center">
        <div className="w-full h-full md:w-1/2 bg-[#45474b] rounded-lg p-6 shadow-md">
          <h1 className="text-2xl font-bold mb-2 text-[#f5f7f8]">
            {selectedPoll?.creator_name}
          </h1>
          {selectedPoll?.question && (
            <p className="mb-4 text-sm text-gray-300">
              {selectedPoll?.question}
            </p>
          )}
          <section>
            <h2 className="text-lg font-semibold mb-2 text-[#f5f7f8]">
              Options
            </h2>
            <ul className="space-y-3">
              {selectedPoll?.options.map((opt: string, idx: number) => (
                <li
                  key={opt ?? idx}
                  className="p-3 rounded-md bg-[#6a6b6e] text-[#f5f7f8]"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{opt}</span>
                    <span className="font-light">
                      {selectedPoll.option_ids.at(idx)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        </div>
        <div className="w-full md:w-1/2 bg-[#45474b] text-[#f5f7f8] rounded-lg p-6 shadow">
          {"TODO: Insert diagrams for vote-distribution"}
        </div>
      </div>
    </div>
  );
}
