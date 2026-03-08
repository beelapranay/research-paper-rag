interface UserMessageProps {
  content: string;
}

const UserMessage = ({ content }: UserMessageProps) => {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] rounded-xl rounded-tr-sm bg-primary text-primary-foreground px-4 py-3 shadow-sm">
        <p className="text-sm leading-relaxed whitespace-pre-wrap">{content}</p>
      </div>
    </div>
  );
};

export default UserMessage;
