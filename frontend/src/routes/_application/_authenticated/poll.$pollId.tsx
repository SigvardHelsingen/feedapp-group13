import { createFileRoute, useNavigate } from "@tanstack/react-router";
import {
  getPollByIdOptions,
  submitVoteMutation,
} from "@/client/@tanstack/react-query.gen";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Check } from "lucide-react";
import { Pie } from "react-chartjs-2";
import { useLivePollVoteCounts } from "@/lib/pollVoteUpdates";

ChartJS.register(ArcElement, Tooltip, Legend);
ChartJS.defaults.color = "#f5f7f8";

export const Route = createFileRoute(
  "/_application/_authenticated/poll/$pollId",
)({
  component: PollComponent,
});

function PollComponent() {
  const { pollId } = Route.useParams();
  const navigate = useNavigate();
  const {
    data: selectedPoll,
    error,
    refetch: refetchPoll,
  } = useQuery({
    ...getPollByIdOptions({
      path: {
        poll_id: parseInt(pollId, 10),
      },
    }),
    retry: false,
  });

  useEffect(() => {
    if (error != null) {
      navigate({ to: "/" });
    }
  });

  const pollOptionVotes = useLivePollVoteCounts(parseInt(pollId, 10));

  const [status, setStatus] = useState("");
  const submitVote = useMutation({
    ...submitVoteMutation(),
    onError: () => {
      setStatus("Registration failed");
    },
    onSuccess: () => {
      setStatus("Registration completed");

      // Hopefully this will call after the update has been processed.
      // TODO: Ideally, we should also optimistically update the state it refers to.
      setTimeout(refetchPoll, 300);
    },
  });

  function onSubmitVote(id: number) {
    submitVote.mutate({
      body: {
        poll_id: parseInt(pollId, 10),
        vote_option_id: id,
      },
    });
  }

  const votes = pollOptionVotes.map((item) => item.vote_count);

  const chartData = {
    labels: selectedPoll?.options,
    datasets: [
      {
        label: "# of Votes",
        data: votes,
        backgroundColor: [
          "rgba(255, 99, 132, 0.7)",
          "rgba(54, 162, 235, 0.7)",
          "rgba(255, 206, 86, 0.7)",
          "rgba(75, 192, 192, 0.7)",
          "rgba(153, 102, 255, 0.7)",
          "rgba(255, 159, 64, 0.7)",
        ],
        borderColor: [
          "rgba(255, 99, 132, 1)",
          "rgba(54, 162, 235, 1)",
          "rgba(255, 206, 86, 1)",
          "rgba(75, 192, 192, 1)",
          "rgba(153, 102, 255, 1)",
          "rgba(255, 159, 64, 1)",
        ],
        borderWidth: 1,
      },
    ],
  };

  return (
    <div className="p-6 min-h-screen w-full flex justify-center items-center">
      <div className="flex flex-col md:flex-row gap-8 justify-center items-start w-full max-w-6xl">
        <div className="w-full md:w-2/3 bg-[#45474b] rounded-lg p-10 shadow-xl min-h-[60vh]">
          <h1 className="text-3xl font-bold mb-3 text-[#f5f7f8]">
            {selectedPoll?.creator_name}
          </h1>
          {selectedPoll?.question && (
            <p className="mb-6 text-base text-gray-300">
              {selectedPoll?.question}
            </p>
          )}
          <section>
            <div className="flex justify-between items-center mb-3">
              <h2 className="text-xl font-semibold text-[#f5f7f8]">Options</h2>
              <h2 className="text-xl font-semibold text-[#f5f7f8]">Votes</h2>
            </div>
            <ul className="space-y-4">
              {selectedPoll?.options.map((opt: string, idx: number) => (
                <li
                  key={opt ?? idx}
                  onClick={() => {
                    onSubmitVote(selectedPoll.option_ids[idx]);
                  }}
                  className="p-4 md:p-6 rounded-md bg-[#6a6b6e] text-[#f5f7f8] cursor-pointer hover:ring-1 active:bg-[#45474b]"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-lg">{opt}</span>
                    <div className="flex justify-center items-center gap-4">
                      <span className="font-light text-lg">
                        {pollOptionVotes
                          ? (pollOptionVotes[idx]?.vote_count ?? 0)
                          : ""}
                      </span>
                      {selectedPoll.user_vote ==
                        selectedPoll.option_ids[idx] && <Check />}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        </div>

        <div className="flex justify-center items-center w-full md:w-1/3 bg-[#45474b] text-[#f5f7f8] rounded-lg p-8 shadow min-h-[60vh]">
          <Pie data={chartData}></Pie>
        </div>
      </div>
    </div>
  );
}
