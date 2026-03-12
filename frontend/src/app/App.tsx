import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";

import { ChatView } from "@/features/chat/ChatView";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { Sidebar } from "@/features/sidebar/Sidebar";
import { useChatStore } from "@/state/chatStore";
import { useUiStore } from "@/state/uiStore";

export default function App() {
  const connect = useChatStore((s) => s.connect);
  const isSidebarOpen = useUiStore((s) => s.isSidebarOpen);
  const [view, setView] = useState<"chat" | "settings">("chat");

  useEffect(() => {
    connect();
  }, [connect]);

  return (
    <div className="noise flex h-screen bg-background text-foreground overflow-hidden selection:bg-primary/20">
      <AnimatePresence mode="wait">
        {view === "settings" ? (
          <motion.div
            key="settings"
            initial={{ opacity: 0, y: 20, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.98 }}
            transition={{ duration: 0.3, ease: [0.23, 1, 0.32, 1] }}
            className="w-full h-full"
          >
            <SettingsPage onBack={() => setView("chat")} />
          </motion.div>
        ) : (
          <motion.div
            key="chat"
            initial={{ opacity: 0, y: 20, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.98 }}
            transition={{ duration: 0.3, ease: [0.23, 1, 0.32, 1] }}
            className="flex w-full h-full relative"
          >
            <AnimatePresence initial={false}>
              {isSidebarOpen && (
                <motion.div
                  key="sidebar"
                  initial={{ width: 0, opacity: 0 }}
                  animate={{ width: 256, opacity: 1 }}
                  exit={{ width: 0, opacity: 0 }}
                  transition={{ duration: 0.3, ease: [0.23, 1, 0.32, 1] }}
                  className="overflow-hidden flex-shrink-0"
                >
                  <div className="w-64 h-full"> 
                    <Sidebar onOpenSettings={() => setView("settings")} />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <motion.div 
              layout
              className={`flex-1 overflow-hidden relative bg-card border border-border/40 transition-all duration-300 ${
                isSidebarOpen ? "rounded-l-2xl rounded-r-2xl m-2 ml-0" : "rounded-2xl m-2"
              }`}
            >
              <ChatView />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
