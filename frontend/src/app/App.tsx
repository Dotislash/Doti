import { useEffect } from "react";

import { ChatView } from "@/features/chat/ChatView";
import { useChatStore } from "@/state/chatStore";

export default function App() {
  const connect = useChatStore((s) => s.connect);

  useEffect(() => {
    connect();
  }, [connect]);

  return <ChatView />;
}
