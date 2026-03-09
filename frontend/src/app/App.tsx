import { useEffect } from "react";

import { ChatView } from "@/features/chat/ChatView";
import { Sidebar } from "@/features/sidebar/Sidebar";
import { useChatStore } from "@/state/chatStore";

export default function App() {
  const connect = useChatStore((s) => s.connect);

  useEffect(() => {
    connect();
  }, [connect]);

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1">
        <ChatView />
      </div>
    </div>
  );
}
