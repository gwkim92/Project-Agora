"use client";

import { useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

export function JobTabs({ submissions, votes, children }: { submissions: React.ReactNode, votes: React.ReactNode, children?: React.ReactNode }) {
  const [activeTab, setActiveTab] = useState("submissions");

  return (
    <div className="space-y-4">
      <Tabs>
        <TabsList>
          <TabsTrigger value="submissions" active={activeTab === "submissions"} onClick={() => setActiveTab("submissions")}>
            Submissions
          </TabsTrigger>
          <TabsTrigger value="votes" active={activeTab === "votes"} onClick={() => setActiveTab("votes")}>
            Jury Votes
          </TabsTrigger>
        </TabsList>
      </Tabs>
      <TabsContent value="submissions" activeValue={activeTab}>
        {submissions}
      </TabsContent>
      <TabsContent value="votes" activeValue={activeTab}>
        {votes}
      </TabsContent>
    </div>
  );
}
