import { useState, useEffect } from "react";
import type { GetVoteCountsRow } from "@/client";

export function useLivePollVoteCounts(pollId: number) {
  const [pollOptionVotes, setPollOptionVotes] = useState<GetVoteCountsRow[]>(
    [],
  );
  useEffect(() => {
    const sse = new EventSource(`/api/vote/stream/${pollId}`);
    sse.addEventListener("vote_update", (e) => {
      const data = JSON.parse(e.data);
      setPollOptionVotes(data);
    });
    return () => {
      sse.close();
    };
  }, [pollId]);

  return pollOptionVotes;
}
