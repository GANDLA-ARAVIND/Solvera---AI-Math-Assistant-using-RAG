import { useEffect, useState } from 'react';
import Header from '../components/common/Header';
import MathRenderer from '../components/chat/MathRenderer';
import useHistoryStore from '../store/historyStore';
import useAuthStore from '../store/authStore';
import downloadHistoryPdf from '../utils/downloadHistoryPdf';
import {
  Clock,
  Trash2,
  ChevronDown,
  ChevronUp,
  CheckCircle,
  XCircle,
  AlertCircle,
  Search,
  Filter,
  Download,
} from 'lucide-react';

const topicColors = {
  algebra: 'bg-purple-900/40 text-purple-300',
  calculus: 'bg-blue-900/40 text-blue-300',
  geometry: 'bg-green-900/40 text-green-300',
  trigonometry: 'bg-orange-900/40 text-orange-300',
  statistics: 'bg-cyan-900/40 text-cyan-300',
  number_theory: 'bg-rose-900/40 text-rose-300',
};

const ALL_TOPICS = [
  'algebra',
  'calculus',
  'geometry',
  'trigonometry',
  'statistics',
  'number_theory',
];

const VerificationIcon = ({ status }) => {
  if (status === 1)
    return <CheckCircle size={14} className="text-emerald-400" />;
  if (status === -1) return <XCircle size={14} className="text-red-400" />;
  return <AlertCircle size={14} className="text-slate-500" />;
};

const HistoryPage = () => {
  const {
    entries,
    selectedEntry,
    loading,
    fetchHistory,
    fetchDetail,
    deleteEntry,
    clearSelected,
  } = useHistoryStore();
  const { fetchUser, user } = useAuthStore();
  const [expandedId, setExpandedId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [topicFilter, setTopicFilter] = useState('');

  useEffect(() => {
    if (!user) fetchUser();
    fetchHistory();
  }, []);

  const handleExpand = async (id) => {
    if (expandedId === id) {
      setExpandedId(null);
      clearSelected();
      return;
    }
    setExpandedId(id);
    await fetchDetail(id);
  };

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    await deleteEntry(id);
    if (expandedId === id) {
      setExpandedId(null);
      clearSelected();
    }
  };

  const handleDownload = async (e, entry) => {
    e.stopPropagation();
    try {
      const res = await import('../api/axiosInstance').then(m => m.default.get(`/history/${entry.id}`));
      downloadHistoryPdf({ ...entry, ...res.data });
    } catch {
      // Fallback: download with just the query (no solution)
      downloadHistoryPdf(entry);
    }
  };

  // Filter entries by search and topic
  const filteredEntries = entries.filter((e) => {
    const matchesSearch =
      !searchQuery ||
      e.query_text.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesTopic = !topicFilter || e.topic === topicFilter;
    return matchesSearch && matchesTopic;
  });

  return (
    <div className="min-h-screen bg-slate-950">
      <Header />
      <main className="pt-16 px-4">
        <div className="border-b border-slate-700 pb-4">
          <h1 className="text-lg font-semibold text-white flex items-center gap-2">
            <Clock size={20} className="text-blue-400" />
            Solution History
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {filteredEntries.length} of {entries.length} solved problem
            {entries.length !== 1 ? 's' : ''}
          </p>

          {/* Search & Filter bar */}
          <div className="flex flex-col sm:flex-row gap-2 mt-3">
            <div className="relative flex-1">
              <Search
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
              />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search problems..."
                className="w-full bg-slate-800 text-white text-sm rounded-lg pl-9 pr-3 py-2 border border-slate-700 focus:border-blue-500 focus:outline-none placeholder-slate-500"
              />
            </div>
            <div className="relative">
              <Filter
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
              />
              <select
                value={topicFilter}
                onChange={(e) => setTopicFilter(e.target.value)}
                className="bg-slate-800 text-white text-sm rounded-lg pl-9 pr-8 py-2 border border-slate-700 focus:border-blue-500 focus:outline-none appearance-none cursor-pointer"
              >
                <option value="">All Topics</option>
                {ALL_TOPICS.map((t) => (
                  <option key={t} value={t}>
                    {t.replace('_', ' ')}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {loading && entries.length === 0 && (
            <p className="text-slate-500 text-center mt-8">Loading...</p>
          )}

          {!loading && entries.length === 0 && (
            <div className="text-center mt-16">
              <Clock size={48} className="text-slate-700 mx-auto mb-3" />
              <p className="text-slate-500">No solved problems yet.</p>
              <p className="text-slate-600 text-sm mt-1">
                Start solving math problems and they'll appear here.
              </p>
            </div>
          )}

          {!loading && entries.length > 0 && filteredEntries.length === 0 && (
            <div className="text-center mt-16">
              <Search size={48} className="text-slate-700 mx-auto mb-3" />
              <p className="text-slate-500">No results match your search.</p>
              <p className="text-slate-600 text-sm mt-1">
                Try a different search query or clear the filter.
              </p>
            </div>
          )}

          <div className="max-w-3xl mx-auto space-y-2">
            {filteredEntries.map((entry) => (
              <div
                key={entry.id}
                className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden"
              >
                {/* Header */}
                <button
                  onClick={() => handleExpand(entry.id)}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-800 transition-colors text-left"
                >
                  <VerificationIcon status={entry.sympy_verified} />
                  <span className="flex-1 text-sm text-slate-200 truncate">
                    {entry.query_text}
                  </span>
                  {entry.topic && (
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${topicColors[entry.topic] || 'bg-slate-700 text-slate-300'}`}
                    >
                      {entry.topic.replace('_', ' ')}
                    </span>
                  )}
                  <span className="text-xs text-slate-500 shrink-0">
                    {entry.created_at
                      ? new Date(entry.created_at).toLocaleDateString()
                      : ''}
                  </span>
                  <button
                    onClick={(e) => handleDownload(e, entry)}
                    className="p-1 text-slate-600 hover:text-blue-400 transition-colors shrink-0"
                    title="Download as PDF"
                  >
                    <Download size={14} />
                  </button>
                  <button
                    onClick={(e) => handleDelete(e, entry.id)}
                    className="p-1 text-slate-600 hover:text-red-400 transition-colors shrink-0"
                  >
                    <Trash2 size={14} />
                  </button>
                  {expandedId === entry.id ? (
                    <ChevronUp size={16} className="text-slate-500 shrink-0" />
                  ) : (
                    <ChevronDown
                      size={16}
                      className="text-slate-500 shrink-0"
                    />
                  )}
                </button>

                {/* Expanded content */}
                {expandedId === entry.id && selectedEntry && (
                  <div className="border-t border-slate-700 px-4 py-4 bg-slate-900/50">
                    <MathRenderer content={selectedEntry.solution_text} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
};

export default HistoryPage;
