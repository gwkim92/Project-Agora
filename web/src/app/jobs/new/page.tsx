import { redirect } from "next/navigation";

export default function OldNewJobRedirect() {
  redirect("/quests/new");
}

