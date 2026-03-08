import ChatTopBar from "./ChatTopBar";
import MessageThread from "./MessageThread";
import InputBar from "./InputBar";

const ChatPanel = () => {
  return (
    <div className="flex flex-col h-full">
      <ChatTopBar />
      <MessageThread />
      <InputBar />
    </div>
  );
};

export default ChatPanel;
