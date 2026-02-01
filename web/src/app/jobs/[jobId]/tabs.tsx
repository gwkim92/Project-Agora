"use client";

import { useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

export function JobTabs({
  submissions,
  votes,
  discussion,
  children,
}: {
  submissions: React.ReactNode;
  votes: React.ReactNode;
  discussion: React.ReactNode;
  children?: React.ReactNode;
}) {
  const [activeTab, setActiveTab] = useState("submissions");

  return (
    <div className="space-y-4">
      <Tabs>
        <TabsList>
          <TabsTrigger value="submissions" active={activeTab === "submissions"} onClick={() => setActiveTab("submissions")}>
            Submissions
          </TabsTrigger>
          <TabsTrigger value="discussion" active={activeTab === "discussion"} onClick={() => setActiveTab("discussion")}>
            Discussion
          </TabsTrigger>
          <TabsTrigger value="votes" active={activeTab === "votes"} onClick={() => setActiveTab("votes")}>
            Jury Votes
          </TabsTrigger>
          <TabsTrigger value="final" active={activeTab === "final"} onClick={() => setActiveTab("final")}>
            Final Decision
          </TabsTrigger>
        </TabsList>
      </Tabs>
      <TabsContent value="submissions" activeValue={activeTab}>
        {submissions}
      </TabsContent>
      <TabsContent value="discussion" activeValue={activeTab}>
        {discussion}
      </TabsContent>
      <TabsContent value="votes" activeValue={activeTab}>
        {votes}
      </TabsContent>
      <TabsContent value="final" activeValue={activeTab}>
        {children}
      </TabsContent>
    </div>
  );
}
