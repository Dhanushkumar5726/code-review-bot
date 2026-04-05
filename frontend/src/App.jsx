import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Bot, User, Edit, Search, Send, Loader2, Sparkles, AlertTriangle, PanelLeftClose, PanelLeftOpen } from 'lucide-react';

function App() {
  const [sessions, setSessions] = useState({
    "Chat 1": [
      {
        role: "assistant",
        content: "Hello! I'm your AI Code Reviewer.\n\nPaste your Python code below, and I'll analyze it, find bugs, and suggest improvements. 🚀"
      }
    ]
  });
  const [currentSession, setCurrentSession] = useState("Chat 1");
  const [sessionCounter, setSessionCounter] = useState(1);
  const [inputCode, setInputCode] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusText, setStatusText] = useState('');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const chatEndRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [sessions, currentSession, statusText]);

  const handleNewChat = () => {
    const newCount = sessionCounter + 1;
    const newName = `Chat ${newCount}`;
    setSessionCounter(newCount);
    setSessions(prev => ({
      ...prev,
      [newName]: [
        {
          role: "assistant",
          content: "Hello! I'm your AI Code Reviewer.\n\nPaste your Python code below, and I'll analyze it, find bugs, and suggest improvements. 🚀"
        }
      ]
    }));
    setCurrentSession(newName);
  };

  const currentChat = sessions[currentSession] || [];

  const handleSend = async () => {
    if (!inputCode.trim() || isProcessing) return;

    const userMessage = `Please review this code:\n\n\`\`\`python\n${inputCode}\n\`\`\``;
    
    // Add user message to current chat
    setSessions(prev => ({
      ...prev,
      [currentSession]: [
        ...prev[currentSession],
        { role: "user", content: userMessage }
      ]
    }));

    setInputCode('');
    setIsProcessing(true);
    setStatusText('🕵️‍♂️ Starting analysis...');

    try {
      // Connect to FastAPI SSE Endpoint
      const response = await fetch('http://localhost:8000/review', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code: inputCode, max_iterations: 1 })
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      // Read SSE stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let streamData = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        streamData += chunk;

        // Simple SSE parsing
        const lines = streamData.split('\n');
        
        let newStreamData = '';
        
        for (let i = 0; i < lines.length; i++) {
          const line = lines[i];
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            if (dataStr) {
                try {
                    const data = JSON.parse(dataStr);
                    if (data.type === 'status') {
                        setStatusText(data.message);
                    } else if (data.type === 'report') {
                        // Analysis complete! Add assistant response
                        setSessions(prev => ({
                            ...prev,
                            [currentSession]: [
                                ...prev[currentSession],
                                { role: "assistant", content: data.content }
                            ]
                        }));
                        setStatusText('');
                    } else if (data.type === 'error') {
                        setSessions(prev => ({
                            ...prev,
                            [currentSession]: [
                                ...prev[currentSession],
                                { role: "assistant", content: data.message }
                            ]
                        }));
                        setStatusText('');
                    }
                } catch(e) {
                    // JSON parse error, ignore and continue collecting chunks
                }
            }
          }
        }
        
        // Retain the last possibly incomplete piece
        // Actually for simplicity, assume line breaks are neat in SSE
        streamData = ''; 
      }

    } catch (error) {
      console.error(error);
      setSessions(prev => ({
        ...prev,
        [currentSession]: [
          ...prev[currentSession],
          { role: "assistant", content: `🚨 **Pipeline Interrupted:** Could not connect to API.\n\nMake sure the FastAPI server is running on http://localhost:8000.` }
        ]
      }));
      setStatusText('');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleSend();
    }
  };

  return (
    <div className="flex h-screen bg-[#0e1117] text-gray-100 overflow-hidden font-sans">
      
      {/* Sidebar */}
      <div className={`${isSidebarOpen ? 'w-[300px] p-3 border-r' : 'w-0 p-0 border-r-0'} transition-all duration-300 flex flex-col bg-[#161b22] border-[#30363d] z-10 hidden md:flex shrink-0 overflow-hidden whitespace-nowrap`}>
        <div className="flex items-center justify-between mb-2">
            <button 
            onClick={handleNewChat}
            className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-[#30363d] transition-colors text-[15px] flex-1 mr-2"
            >
            <div className="bg-[#1e293b] p-1.5 rounded-md border border-[#30363d]">
                <Edit className="w-4 h-4 text-gray-200" />
            </div>
            <span className="font-medium">New chat</span>
            </button>

            <button 
               onClick={() => setIsSidebarOpen(false)}
               className="p-2 rounded-lg hover:bg-[#30363d] transition-colors text-gray-400 hover:text-gray-200 shrink-0"
               title="Close sidebar"
            >
               <PanelLeftClose className="w-5 h-5" />
            </button>
        </div>

        <button className="flex justify-between items-center p-3 rounded-lg hover:bg-[#30363d] transition-colors mb-6 text-[15px] group text-gray-400 hover:text-gray-200">
           <span className="font-medium">Search chats</span>
           <Search className="w-5 h-5 invisible group-hover:visible" />
        </button>
        
        <div className="flex-1 overflow-y-auto pr-2">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 px-2">Your chats</h3>
            
            <div className="flex flex-col gap-1">
                {Object.keys(sessions).reverse().map(sessionName => (
                <button
                    key={sessionName}
                    onClick={() => setCurrentSession(sessionName)}
                    className={`text-left px-3 py-2.5 rounded-lg transition-colors text-[14px] truncate ${
                    sessionName === currentSession ? 'bg-[#30363d] text-white font-medium' : 'text-gray-400 hover:bg-[#21262d] hover:text-gray-200'
                    }`}
                >
                    {sessionName}
                </button>
                ))}
            </div>
        </div>

        <div className="mt-4 pt-4 border-t border-[#30363d]">
            <div className="flex items-center gap-3 px-2 pb-2">
                 <img src="/logo.png" alt="Logo" className="w-8 h-8 rounded shrink-0 object-cover" />
                 <span className="text-sm font-medium">Code Reviewer</span>
            </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col relative h-full w-full overflow-hidden">
        
        {/* Floating Top Left Buttons (Desktop when sidebar is closed) */}
        {!isSidebarOpen && (
            <div className="absolute top-4 left-4 z-20 flex gap-2 hidden md:flex">
                <button 
                    onClick={() => setIsSidebarOpen(true)}
                    className="p-2 rounded-lg hover:bg-[#30363d] transition-colors text-gray-400 hover:text-gray-200"
                    title="Open sidebar"
                >
                    <PanelLeftOpen className="w-5 h-5" />
                </button>
                <button 
                    onClick={handleNewChat}
                    className="p-2 rounded-lg hover:bg-[#30363d] transition-colors text-gray-400 hover:text-gray-200"
                    title="New chat"
                >
                    <Edit className="w-5 h-5" />
                </button>
            </div>
        )}

        {/* Header (Mobile) */}
        <div className="md:hidden flex items-center justify-between p-4 border-b border-[#30363d] bg-[#161b22]">
           <div className="flex items-center gap-2">
              <img src="/logo.png" alt="Logo" className="w-7 h-7 rounded" />
              <span className="font-medium">Code Reviewer</span>
           </div>
           <button onClick={handleNewChat}><Edit className="w-5 h-5" /></button>
        </div>

        {/* Chat History */}
        <div className="flex-1 overflow-y-auto px-4 md:px-20 py-8">
            <div className="max-w-4xl mx-auto flex flex-col gap-6 lg:gap-8 pb-4">
                
                {/* Hero / Header at start of chat */}
                {currentChat.length <= 1 && (
                    <div className="text-center mt-10 mb-12 animate-in fade-in slide-in-from-bottom-4 duration-700">
                        <h1 className="text-4xl md:text-5xl font-bold hero-title mb-3">Iterative Code Review Bot</h1>
                        <p className="text-gray-400 text-lg md:text-xl font-light">Powered by LangGraph + AI — Analyze, Fix, Repeat</p>
                    </div>
                )}

                {/* Messages */}
                {currentChat.map((msg, i) => (
                    <div key={i} className={`flex gap-4 md:gap-6 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                        
                        {msg.role === 'assistant' && (
                            <div className="w-8 h-8 rounded-full shadow-lg bg-white shrink-0 overflow-hidden flex items-center justify-center">
                                <img src="/logo.png" className="w-full h-full object-cover" alt="AI" />
                            </div>
                        )}

                        <div className={`
                            ${msg.role === 'user' 
                                ? 'bg-[#30363d] p-4 rounded-2xl rounded-tr-sm max-w-[85%]' 
                                : 'flex-1 p-1 max-w-[95%] text-gray-200'
                            }
                        `}>
                            {msg.role === 'user' ? (
                                <pre className="whitespace-pre-wrap font-mono text-[14px]">
                                    {msg.content.replace('Please review this code:\n\n```python\n','').replace('\n```','')}
                                </pre>
                            ) : (
                                <div className="prose prose-invert max-w-none prose-pre:bg-transparent prose-pre:border-none prose-pre:p-0">
                                   <ReactMarkdown 
                                       remarkPlugins={[remarkGfm]}
                                       components={{
                                           code({node, inline, className, children, ...props}) {
                                               const match = /language-(\w+)/.exec(className || '')
                                               return !inline && match ? (
                                                   <SyntaxHighlighter
                                                       {...props}
                                                       children={String(children).replace(/\n$/, '')}
                                                       style={vscDarkPlus}
                                                       language={match[1]}
                                                       PreTag="div"
                                                       className="rounded-lg !bg-[#161b22] border border-[#30363d]"
                                                   />
                                               ) : (
                                                   <code {...props} className={className}>
                                                       {children}
                                                   </code>
                                               )
                                           }
                                       }}
                                   >
                                       {msg.content}
                                   </ReactMarkdown>
                                </div>
                            )}
                        </div>
                    </div>
                ))}

                {/* Status Indicator during processing */}
                {isProcessing && statusText && (
                    <div className="flex gap-4 md:gap-6 animate-in fade-in duration-300">
                         <div className="w-8 h-8 rounded-full shadow-lg bg-white shrink-0 overflow-hidden flex items-center justify-center">
                            <img src="/logo.png" className="w-full h-full object-cover" alt="AI" />
                         </div>
                         <div className="flex items-center gap-3 text-indigo-400 font-medium">
                            <Loader2 className="w-5 h-5 animate-spin" />
                            <span>{statusText}</span>
                         </div>
                    </div>
                )}
                
                <div ref={chatEndRef} />
            </div>
        </div>

        {/* Input Area */}
        <div className="w-full shrink-0 p-4 md:px-20 bg-[#0e1117] pb-8">
            <div className="max-w-4xl mx-auto relative glass-panel rounded-2xl p-2 md:p-3 shadow-2xl flex flex-col focus-within:ring-2 focus-within:ring-indigo-500/50 transition-all">
                <textarea 
                    value={inputCode}
                    onChange={(e) => setInputCode(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Paste your Python code here... (Cmd/Ctrl + Enter to send)"
                    className="w-full bg-transparent border-none resize-none focus:outline-none text-[15px] p-2 min-h-[90px] max-h-[300px] overflow-y-auto text-gray-200 placeholder-gray-500 font-mono"
                    disabled={isProcessing}
                />
                
                <div className="flex justify-between items-center mt-2 px-2 pb-1">
                    <div className="text-xs text-gray-500 flex items-center gap-1.5">
                        <Sparkles className="w-4 h-4" /> AI can make mistakes. Please verify.
                    </div>
                    <button 
                        onClick={handleSend}
                        disabled={!inputCode.trim() || isProcessing}
                        className={`p-2 rounded-xl transition-all duration-300 flex items-center justify-center ${
                             inputCode.trim() && !isProcessing
                                 ? 'btn-primary text-white cursor-pointer'
                                 : 'bg-[#30363d] text-gray-400 cursor-not-allowed'
                        }`}
                    >
                         {isProcessing ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                    </button>
                </div>
            </div>
            
            <div className="text-center mt-3 text-xs text-gray-500 pb-2">
                Powered by LangGraph Core + React Frontend
            </div>
        </div>

      </div>
    </div>
  );
}

export default App;
