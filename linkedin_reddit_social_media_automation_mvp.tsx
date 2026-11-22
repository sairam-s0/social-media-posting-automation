import React, { useState, useEffect, useRef } from 'react';
import {
  LayoutDashboard,
  PenTool,
  FileText,
  Calendar,
  Key,
  CheckCircle2,
  AlertCircle,
  Clock,
  Send,
  RefreshCw,
  Trash2,
  ChevronRight,
  ChevronLeft,
  Sparkles,
  Terminal,
  Share2,
  Search,
  Filter,
  ExternalLink,
  Edit3,
  X,
  Globe,
  Check,
  AlertTriangle,
  Lock,
  Copy,
  Settings,
  ShieldCheck,
  Info
} from 'lucide-react';
import CalendarPicker from './src/CalendarPicker.jsx';

// Clean initial defaults (no hardcoded usernames, no dummy sample posts)
const DEFAULT_ACCOUNTS = {
  linkedin: {
    connected: false,
    accountName: '',
    profileId: '',
    tokenExpiry: null,
    avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=80',
    scope: 'openid profile w_member_social'
  },
  reddit: {
    connected: false,
    accountName: '',
    subreddits: ['r/smallbusiness', 'r/entrepreneur', 'r/SaaS', 'r/webdev'],
    tokenExpiry: null,
    avatar: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop&q=80',
    scope: 'identity submit'
  }
};

const DEFAULT_POSTS = [];

let bootstrapPromise = null;

export const initSessionConfig = async () => {
  if (window.__APP_CONFIG__?.sessionToken) {
    return window.__APP_CONFIG__;
  }
  if (!bootstrapPromise) {
    bootstrapPromise = (async () => {
      try {
        const res = await fetch('/api/bootstrap');
        if (res.ok) {
          const data = await res.json();
          window.__APP_CONFIG__ = {
            ...(window.__APP_CONFIG__ || {}),
            sessionToken: data.session_token,
            host: data.host,
            port: data.port,
            apiBase: data.api_base || '/api',
            redirectUris: data.redirect_uris,
            sharedOAuth: data.shared_oauth,
            limits: data.limits,
          };
        }
      } catch (err) {
        console.warn('Bootstrap fetch failed:', err);
      }
      return window.__APP_CONFIG__ || {};
    })();
  }
  return bootstrapPromise;
};

export const getSessionToken = () => {
  return window.__APP_CONFIG__?.sessionToken || '';
};

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [accounts, setAccounts] = useState(() => DEFAULT_ACCOUNTS);
  const [posts, setPosts] = useState(() => DEFAULT_POSTS);
  const [logs, setLogs] = useState([]);
  const [isLogDrawerOpen, setIsLogDrawerOpen] = useState(false);
  const [toast, setToast] = useState(null);
  const oauthPollRef = useRef(null);

  // User detected timezone
  const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';

  // Integrations & Settings State
  const [integrations, setIntegrations] = useState({
    groq: { configured: false, masked: '' },
    linkedin: { configured: false, client_id_masked: '', redirect_uri: 'http://127.0.0.1:8000/auth/linkedin/callback', status: {} },
    reddit: { configured: false, client_id_masked: '', user_agent: '', redirect_uri: 'http://127.0.0.1:8000/auth/reddit/callback', status: {} },
  });

  const [integrationForm, setIntegrationForm] = useState({
    groq_api_key: '',
    linkedin_client_id: '',
    linkedin_client_secret: '',
    linkedin_redirect_uri: '',
    reddit_client_id: '',
    reddit_client_secret: '',
    reddit_user_agent: 'AutoSocialPoster/1.0 by u/YourUsername',
    reddit_redirect_uri: '',
  });

  const [licenseStatus, setLicenseStatus] = useState({
    activated: false,
    license_key: '',
    message: 'Loading status...'
  });
  const [licenseKeyInput, setLicenseKeyInput] = useState('');
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const [showCustomLi, setShowCustomLi] = useState(false);
  const [showCustomRd, setShowCustomRd] = useState(false);

  // Content Generation Form State
  const [genForm, setGenForm] = useState({
    topic: '',
    mainMessage: '',
    targetAudience: '',
    tone: 'Thought Leadership',
    websiteUrl: '',
    subreddit: 'r/smallbusiness',
    referencePost: ''
  });

  const [generatedContent, setGeneratedContent] = useState({
    linkedin: '',
    reddit: ''
  });
  const [isGenerating, setIsGenerating] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [filterStatus, setFilterStatus] = useState('all');

  // Format local Date as YYYY-MM-DD
  const formatLocalDate = (d) => {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  };

  // Tomorrow formatted for initial default scheduling (local calendar day)
  const getTomorrowStr = () => {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    return formatLocalDate(d);
  };

  // 1. Application-Style Scheduling Modal State
  const [scheduleModal, setScheduleModal] = useState({
    isOpen: false,
    post: null, // existing post or null for newly drafted post
    platform: 'linkedin', // 'linkedin' | 'reddit' | 'both'
    destination: 'Personal Profile (Feed)',
    date: getTomorrowStr(),
    time: '10:00',
    topic: '',
    content: '',
    confirmDateTime: false,
    confirmAutoPublish: false
  });

  // 2. Edit Scheduled Post Modal State
  const [editModal, setEditModal] = useState({
    isOpen: false,
    post: null,
    content: '',
    destination: '',
    date: '',
    time: '10:00',
    topic: ''
  });

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const addLog = (endpoint, method, status, payload) => {
    const newLog = {
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date().toLocaleTimeString(),
      endpoint,
      method,
      status,
      payload
    };
    setLogs((prev) => [newLog, ...prev.slice(0, 49)]);
  };

  // Relative API client with automatic session token initialization and 401 retry
  const apiRequest = async (path, options = {}) => {
    if (!window.__APP_CONFIG__?.sessionToken) {
      await initSessionConfig();
    }

    const apiBase = window.__APP_CONFIG__?.apiBase || '/api';
    const cleanPath = path.startsWith('/api') ? path : `${apiBase}${path}`;
    const token = getSessionToken();

    const headers = {
      'Content-Type': 'application/json',
      ...(token ? { 'X-Session-Token': token } : {}),
      ...(options.headers || {})
    };

    let response = await fetch(cleanPath, {
      ...options,
      headers
    });

    // Auto-retry once on 401 in case token expired or backend restarted
    if (response.status === 401 && !options._retried) {
      bootstrapPromise = null;
      if (window.__APP_CONFIG__) {
        window.__APP_CONFIG__.sessionToken = '';
      }
      await initSessionConfig();
      const newToken = getSessionToken();
      if (newToken) {
        return apiRequest(path, {
          ...options,
          _retried: true,
          headers: {
            ...(options.headers || {}),
            'X-Session-Token': newToken
          }
        });
      }
    }

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const err = data.detail || data.error || `Request failed (${response.status})`;
      throw new Error(err);
    }
    return data;
  };

  const refreshAccounts = async () => {
    try {
      const current = await apiRequest('/accounts');
      setAccounts((prev) => ({
        ...prev,
        linkedin: {
          ...prev.linkedin,
          connected: current.linkedin?.connected || false,
          accountName: current.linkedin?.account_name || '',
          daysRemaining: current.linkedin?.days_remaining ?? 0,
          expiresSoon: current.linkedin?.expires_soon || false
        },
        reddit: {
          ...prev.reddit,
          connected: current.reddit?.connected || false,
          accountName: current.reddit?.account_name || '',
          daysRemaining: current.reddit?.days_remaining ?? 0,
          expiresSoon: current.reddit?.expires_soon || false
        }
      }));
    } catch { /* Backend offline or initializing */ }
  };

  const refreshPosts = async () => {
    try {
      const serverPosts = await apiRequest('/posts');
      if (Array.isArray(serverPosts)) {
        setPosts(serverPosts.map((p) => ({
          id: p.id,
          topic: p.topic,
          platform: p.platform,
          destination: p.destination || p.subreddit || (p.platform === 'linkedin' ? 'Personal Profile (Feed)' : 'r/smallbusiness'),
          subreddit: p.subreddit || '',
          content: p.content,
          status: p.status,
          approved: Boolean(p.approved),
          createdAt: p.created_at,
          scheduledAt: p.scheduled_at,
          publishedAt: p.published_at,
          externalId: p.external_id,
          errorMessage: p.error,
          timezone: p.timezone || userTimezone
        })));
      }
    } catch { /* Fallback */ }
  };

  const fetchIntegrations = async () => {
    try {
      const data = await apiRequest('/settings/integrations');
      setIntegrations(data);
    } catch { /* Silent */ }
  };

  const fetchLicense = async () => {
    try {
      const data = await apiRequest('/license/status');
      setLicenseStatus(data);
    } catch { /* Silent */ }
  };

  useEffect(() => {
    const initializeAppData = async () => {
      await initSessionConfig();
      refreshAccounts();
      refreshPosts();
      fetchIntegrations();
      fetchLicense();
    };
    initializeAppData();

    // Listen for OAuth completion messages from auth callback popup
    const handleMessage = (e) => {
      if (e.data && e.data.type === 'OAUTH_SUCCESS') {
        showToast(`${e.data.platform?.toUpperCase()} authorized and connected!`);
        refreshAccounts();
        fetchIntegrations();
      }
    };
    window.addEventListener('message', handleMessage);
    return () => {
      window.removeEventListener('message', handleMessage);
      if (oauthPollRef.current) clearInterval(oauthPollRef.current);
    };
  }, []);

  // Stats calculation
  const stats = {
    connectedCount: Object.values(accounts).filter((a) => a.connected).length,
    scheduledCount: posts.filter((p) => p.status === 'scheduled').length,
    publishedCount: posts.filter((p) => p.status === 'published').length,
    missedCount: posts.filter((p) => p.status === 'missed').length,
    failedCount: posts.filter((p) => p.status === 'failed').length,
    draftCount: posts.filter((p) => p.status === 'draft').length,
    cancelledCount: posts.filter((p) => p.status === 'cancelled').length
  };

  const handleDisconnect = async (platform) => {
    if (!window.confirm(`Disconnect ${platform.toUpperCase()} and remove stored authorization tokens?`)) return;
    try {
      await apiRequest(`/accounts/${platform}/disconnect`, { method: 'POST' });
      addLog(`/accounts/${platform}/disconnect`, 'POST', 200, { platform });
      showToast(`${platform.toUpperCase()} disconnected and credentials wiped.`);
      await refreshAccounts();
      await fetchIntegrations();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const startOAuthPolling = (platform) => {
    if (oauthPollRef.current) {
      clearInterval(oauthPollRef.current);
    }
    let attempts = 0;
    const maxAttempts = 90; // Poll for 3 minutes (every 2s)
    oauthPollRef.current = setInterval(async () => {
      attempts++;
      try {
        const current = await apiRequest('/accounts');
        if (current && current[platform]?.connected) {
          clearInterval(oauthPollRef.current);
          oauthPollRef.current = null;
          showToast(`${platform.toUpperCase()} authorized and connected successfully!`);
          await refreshAccounts();
          await fetchIntegrations();
        }
      } catch {
        // Retry polling silently
      }
      if (attempts >= maxAttempts) {
        if (oauthPollRef.current) {
          clearInterval(oauthPollRef.current);
          oauthPollRef.current = null;
        }
      }
    }, 2000);
  };

  const handleResetToShared = async (platform) => {
    try {
      showToast(`Reverting ${platform === 'linkedin' ? 'LinkedIn' : 'Reddit'} to Central Shared App...`);
      const res = await apiRequest(`/settings/integrations/${platform}/reset-to-shared`, { method: 'POST' });
      if (res?.success) {
        showToast(`Reverted to Central Shared App successfully.`, 'success');
        if (platform === 'linkedin') {
          setIntegrationForm(prev => ({ ...prev, linkedin_client_id: '', linkedin_client_secret: '', linkedin_redirect_uri: '' }));
        } else {
          setIntegrationForm(prev => ({ ...prev, reddit_client_id: '', reddit_client_secret: '', reddit_redirect_uri: '' }));
        }
        await fetchIntegrations();
        await refreshAccounts();
      }
    } catch (err) {
      showToast(`Reset Failed: ${err.message}`, 'error');
    }
  };

  const handleSaveIntegrations = async () => {
    setIsSavingSettings(true);
    try {
      const payload = {};
      if (integrationForm.groq_api_key.trim()) payload.groq_api_key = integrationForm.groq_api_key.trim();
      if (integrationForm.linkedin_client_id.trim()) payload.linkedin_client_id = integrationForm.linkedin_client_id.trim();
      if (integrationForm.linkedin_client_secret.trim()) payload.linkedin_client_secret = integrationForm.linkedin_client_secret.trim();
      if (integrationForm.linkedin_redirect_uri.trim()) payload.linkedin_redirect_uri = integrationForm.linkedin_redirect_uri.trim();
      if (integrationForm.reddit_client_id.trim()) payload.reddit_client_id = integrationForm.reddit_client_id.trim();
      if (integrationForm.reddit_client_secret.trim()) payload.reddit_client_secret = integrationForm.reddit_client_secret.trim();
      if (integrationForm.reddit_user_agent.trim()) payload.reddit_user_agent = integrationForm.reddit_user_agent.trim();
      if (integrationForm.reddit_redirect_uri.trim()) payload.reddit_redirect_uri = integrationForm.reddit_redirect_uri.trim();

      const res = await apiRequest('/settings/integrations', {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      if (!res || !res.success) {
        throw new Error(res?.error || 'Failed to save integration settings.');
      }

      showToast('Credentials safely encrypted in Windows Credential Manager.');
      setIntegrationForm((prev) => ({
        ...prev,
        groq_api_key: '',
        linkedin_client_secret: '',
        reddit_client_secret: ''
      }));
      await fetchIntegrations();
      return true;
    } catch (err) {
      showToast(`Save Failed: ${err.message}`, 'error');
      return false;
    } finally {
      setIsSavingSettings(false);
    }
  };

  const handleConnect = async (platform, customRedirectUri = null) => {
    try {
      showToast(`Opening ${platform === 'linkedin' ? 'LinkedIn' : 'Reddit'} in default browser...`);
      const body = customRedirectUri ? JSON.stringify({ redirect_uri: customRedirectUri }) : undefined;
      const launchRes = await apiRequest(`/auth/${platform}/open-browser`, {
        method: 'POST',
        body
      });
      if (!launchRes?.success) {
        throw new Error(launchRes?.error || 'Unable to open system browser');
      }
      showToast(`Please complete authorization in your browser window.`, 'success');
      startOAuthPolling(platform);
    } catch (err) {
      showToast(`Browser Launch Error: ${err.message}`, 'error');
    }
  };

  const handleSaveAndConnect = async (platform) => {
    // 1. If form has unsaved custom credentials, save them first
    const hasInputsToSave =
      (platform === 'linkedin' && (integrationForm.linkedin_client_id.trim() || integrationForm.linkedin_client_secret.trim() || integrationForm.linkedin_redirect_uri.trim())) ||
      (platform === 'reddit' && (integrationForm.reddit_client_id.trim() || integrationForm.reddit_client_secret.trim() || integrationForm.reddit_user_agent.trim() || integrationForm.reddit_redirect_uri.trim()));

    if (hasInputsToSave) {
      const saveSuccess = await handleSaveIntegrations();
      if (!saveSuccess) {
        return;
      }
    }

    // 2. Launch OAuth in the operating system's default browser
    const chosenUri = platform === 'linkedin' ? (integrationForm.linkedin_redirect_uri.trim() || null) : (integrationForm.reddit_redirect_uri.trim() || null);
    await handleConnect(platform, chosenUri);
  };

  const handleActivateLicense = async () => {
    if (!licenseKeyInput.trim()) {
      showToast('Please enter a license key to activate.', 'error');
      return;
    }
    try {
      const res = await apiRequest('/license/activate', {
        method: 'POST',
        body: JSON.stringify({ license_key: licenseKeyInput.trim() })
      });
      showToast(res.message || 'License activated successfully!');
      setLicenseKeyInput('');
      await fetchLicense();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    showToast('Redirect URI copied to clipboard!');
  };

  const handleGenerateContent = async () => {
    if (!genForm.topic.trim()) {
      showToast('Please enter a topic to generate content.', 'error');
      return;
    }

    setIsGenerating(true);
    addLog('/content/generate', 'POST', 0, {
      topic: genForm.topic,
      tone: genForm.tone,
      target: genForm.targetAudience
    });

    try {
      const result = await apiRequest('/content/generate', {
        method: 'POST',
        body: JSON.stringify({
          topic: genForm.topic,
          main_message: genForm.mainMessage,
          target_audience: genForm.targetAudience,
          tone: genForm.tone,
          website_url: genForm.websiteUrl,
          subreddit: genForm.subreddit,
          reference_post: genForm.referencePost
        })
      });
      setGeneratedContent({ linkedin: result.linkedin, reddit: result.reddit });
      addLog('/content/generate', 'POST', 200, { topic: genForm.topic });
      showToast('Drafts generated in 1 API call with targeted hashtags & hook.');
    } catch (error) {
      addLog('/content/generate', 'POST', 500, { error: error.message });
      showToast(error.message, 'error');
    } finally {
      setIsGenerating(false);
    }
  };

  // Save Draft action
  const saveDraft = async (platform, content, destination) => {
    if (!content.trim()) return;
    try {
      const dest = destination || (platform === 'linkedin' ? 'Personal Profile (Feed)' : genForm.subreddit || 'r/smallbusiness');
      const saved = await apiRequest('/posts', {
        method: 'POST',
        body: JSON.stringify({
          topic: genForm.topic || 'Custom Draft',
          platform,
          content,
          destination: dest,
          subreddit: platform === 'reddit' ? dest : null,
          status: 'draft',
          timezone: userTimezone
        })
      });
      const newPost = {
        id: saved.id,
        topic: genForm.topic || 'Custom Draft',
        platform,
        destination: saved.destination,
        subreddit: platform === 'reddit' ? saved.destination : '',
        content,
        status: 'draft',
        approved: false,
        createdAt: new Date().toISOString(),
        scheduledAt: null,
        publishedAt: null,
        externalId: null,
        errorMessage: null,
        timezone: userTimezone
      };
      setPosts((prev) => [newPost, ...prev]);
      showToast(`${platform.toUpperCase()} draft saved successfully.`);
      return saved.id;
    } catch (error) {
      showToast(error.message, 'error');
      throw error;
    }
  };

  // Publish Now action
  const publishNow = async (postOrDraft) => {
    setIsPublishing(true);
    try {
      let postId = postOrDraft.id;
      if (!postId) {
        const dest = postOrDraft.destination || (postOrDraft.platform === 'linkedin' ? 'Personal Profile (Feed)' : genForm.subreddit || 'r/smallbusiness');
        postId = await saveDraft(postOrDraft.platform, postOrDraft.content, dest);
      }
      const result = await apiRequest(`/posts/${postId}/publish`, { method: 'POST' });
      setPosts((prev) =>
        prev.map((item) =>
          item.id === postId
            ? {
                ...item,
                status: 'published',
                approved: true,
                publishedAt: result.published_at || new Date().toISOString(),
                externalId: result.external_id,
                errorMessage: null
              }
            : item
        )
      );
      addLog(`/posts/${postId}/publish`, 'POST', 200, { platform: postOrDraft.platform });
      showToast(`Published to ${postOrDraft.platform.toUpperCase()} immediately!`);
      await refreshAccounts();
      await refreshPosts();
    } catch (error) {
      addLog('/posts/publish', 'POST', 500, { error: error.message });
      showToast(error.message, 'error');
      await refreshPosts();
    } finally {
      setIsPublishing(false);
    }
  };

  // Open the Scheduling Window/Modal
  const openScheduleModal = (platform, content = '', post = null) => {
    const isLi = platform === 'linkedin';
    const initialDest = post?.destination || (isLi ? 'Personal Profile (Feed)' : (genForm.subreddit || 'r/smallbusiness'));
    setScheduleModal({
      isOpen: true,
      post,
      platform,
      destination: initialDest,
      date: getTomorrowStr(),
      time: '10:00',
      topic: post?.topic || genForm.topic || 'Social Update',
      content: content || post?.content || (isLi ? generatedContent.linkedin : generatedContent.reddit),
      confirmDateTime: false,
      confirmAutoPublish: false
    });
  };

  // Handle Schedule Modal Submit
  const handleScheduleSubmit = async () => {
    if (!scheduleModal.confirmDateTime || !scheduleModal.confirmAutoPublish) {
      showToast('Please check both confirmation boxes to approve automatic scheduling.', 'error');
      return;
    }

    if (!scheduleModal.date) {
      showToast('Please select a date from the 7-day calendar.', 'error');
      return;
    }

    const scheduledIso = `${scheduleModal.date}T${scheduleModal.time}:00`;

    try {
      if (scheduleModal.platform === 'both') {
        const tasks = [];
        if (generatedContent.linkedin) {
          tasks.push(
            apiRequest('/posts', {
              method: 'POST',
              body: JSON.stringify({
                topic: scheduleModal.topic,
                platform: 'linkedin',
                content: generatedContent.linkedin,
                destination: 'Personal Profile (Feed)',
                status: 'scheduled',
                scheduled_at: scheduledIso,
                timezone: userTimezone
              })
            })
          );
        }
        if (generatedContent.reddit) {
          tasks.push(
            apiRequest('/posts', {
              method: 'POST',
              body: JSON.stringify({
                topic: scheduleModal.topic,
                platform: 'reddit',
                content: generatedContent.reddit,
                destination: genForm.subreddit || 'r/smallbusiness',
                subreddit: genForm.subreddit || 'r/smallbusiness',
                status: 'scheduled',
                scheduled_at: scheduledIso,
                timezone: userTimezone
              })
            })
          );
        }
        await Promise.all(tasks);
        await refreshPosts();
        showToast('Both LinkedIn & Reddit posts scheduled successfully!');
      } else {
        const res = await apiRequest('/posts', {
          method: 'POST',
          body: JSON.stringify({
            topic: scheduleModal.topic,
            platform: scheduleModal.platform,
            content: scheduleModal.content,
            destination: scheduleModal.destination,
            subreddit: scheduleModal.platform === 'reddit' ? scheduleModal.destination : null,
            status: 'scheduled',
            scheduled_at: scheduledIso,
            timezone: userTimezone
          })
        });

        const newScheduledPost = {
          id: res.id,
          topic: scheduleModal.topic,
          platform: scheduleModal.platform,
          destination: res.destination,
          subreddit: scheduleModal.platform === 'reddit' ? res.destination : '',
          content: scheduleModal.content,
          status: 'scheduled',
          approved: true,
          createdAt: new Date().toISOString(),
          scheduledAt: res.scheduled_at,
          publishedAt: null,
          externalId: null,
          errorMessage: null,
          timezone: userTimezone
        };
        setPosts((prev) => [newScheduledPost, ...prev]);
        showToast(`Post scheduled for ${scheduleModal.date} at ${scheduleModal.time}!`);
      }
      setScheduleModal((prev) => ({ ...prev, isOpen: false }));
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const openEditModal = (post) => {
    let datePart = getTomorrowStr();
    let timePart = '10:00';
    if (post.scheduledAt) {
      try {
        const d = new Date(post.scheduledAt);
        datePart = formatLocalDate(d);
        timePart = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
      } catch { /* Default */ }
    }
    setEditModal({
      isOpen: true,
      post,
      content: post.content,
      destination: post.destination || (post.platform === 'linkedin' ? 'Personal Profile (Feed)' : 'r/smallbusiness'),
      date: datePart,
      time: timePart,
      topic: post.topic
    });
  };

  const handleEditSave = async () => {
    if (!editModal.content.trim()) {
      showToast('Post content cannot be empty.', 'error');
      return;
    }
    const scheduledIso = `${editModal.date}T${editModal.time}:00`;
    try {
      const res = await apiRequest(`/posts/${editModal.post.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          content: editModal.content,
          destination: editModal.destination,
          scheduled_at: scheduledIso,
          timezone: userTimezone,
          topic: editModal.topic
        })
      });
      setPosts((prev) =>
        prev.map((p) =>
          p.id === editModal.post.id
            ? {
                ...p,
                content: res.content,
                destination: res.destination,
                scheduledAt: res.scheduled_at,
                topic: res.topic,
                timezone: res.timezone
              }
            : p
        )
      );
      setEditModal((prev) => ({ ...prev, isOpen: false }));
      showToast('Scheduled post updated successfully.');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const cancelScheduledPost = async (postId) => {
    if (!window.confirm('Are you sure you want to cancel this scheduled post?')) return;
    try {
      await apiRequest(`/posts/${postId}/cancel`, { method: 'POST' });
      setPosts((prev) =>
        prev.map((p) => (p.id === postId ? { ...p, status: 'cancelled' } : p))
      );
      showToast('Scheduled post cancelled.');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const deletePost = async (postId) => {
    if (!window.confirm('Delete this post permanently?')) return;
    try {
      await apiRequest(`/posts/${postId}`, { method: 'DELETE' });
      setPosts((prev) => prev.filter((p) => p.id !== postId));
      showToast('Post deleted.');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const filteredPosts = posts.filter((p) => {
    if (filterStatus === 'all') return true;
    return p.status === filterStatus;
  });

  const scheduledPosts = posts.filter((p) => p.status === 'scheduled' || p.status === 'missed');

  const formatScheduledTime = (isoString) => {
    if (!isoString) return 'Not set';
    try {
      const d = new Date(isoString);
      return d.toLocaleString([], {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return isoString;
    }
  };

  const getRelativeTimeBadge = (isoString) => {
    if (!isoString) return null;
    const diffMs = new Date(isoString).getTime() - Date.now();
    if (diffMs <= 0) return 'Due now (Auto-publishing)';
    const diffHours = Math.round(diffMs / (1000 * 60 * 60));
    if (diffHours < 24) return `In ~${diffHours} hour${diffHours === 1 ? '' : 's'}`;
    const diffDays = Math.round(diffHours / 24);
    return `In ~${diffDays} day${diffDays === 1 ? '' : 's'}`;
  };

  return (
    <div className="min-h-screen bg-[#FAF8F5] text-[#2C352B] flex flex-col font-sans">
      {/* Toast Notification */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 flex items-center gap-3 px-4 py-3 rounded-lg shadow-md border transition-all ${
            toast.type === 'error'
              ? 'bg-[#FDF2F2] border-[#E5B8B8] text-[#8C2A2A]'
              : toast.type === 'info'
              ? 'bg-[#F0F5F8] border-[#B8D2E5] text-[#2A5C8C]'
              : 'bg-[#F2F6F1] border-[#B2C9B0] text-[#2E542B]'
          }`}
        >
          {toast.type === 'error' ? (
            <AlertCircle className="w-5 h-5 text-[#8C2A2A]" />
          ) : (
            <CheckCircle2 className="w-5 h-5 text-[#2E542B]" />
          )}
          <span className="text-xs font-semibold">{toast.message}</span>
        </div>
      )}

      {/* Main Header */}
      <header className="border-b border-[#E5E0D8] bg-[#F3EFEA] sticky top-0 z-30 px-4 lg:px-8 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-[#3F513D] p-2 rounded-lg text-[#FAF8F5] shadow-sm">
            <Share2 className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-bold text-base text-[#2C352B] leading-tight flex items-center gap-2">
              AutoSocial Console
              <span className="bg-[#E2EBDD] text-[#3F513D] text-[10px] px-2 py-0.5 rounded border border-[#C3D4BC] font-mono">
                Production Suite
              </span>
            </h1>
            <p className="text-[11px] text-[#6B7569] hidden sm:block">LinkedIn & Reddit Automated Publishing Suite (127.0.0.1)</p>
          </div>
        </div>

        {/* Global Navigation */}
        <nav className="hidden md:flex items-center gap-1 bg-[#FAF8F5] p-1 rounded-xl border border-[#E5E0D8]">
          {[
            { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
            { id: 'create', label: 'Create Post', icon: PenTool },
            { id: 'posts', label: 'Posts', icon: FileText, badge: posts.length },
            { id: 'schedule', label: 'Scheduled Queue', icon: Calendar, badge: stats.scheduledCount + stats.missedCount },
            { id: 'settings', label: 'Integrations & Settings', icon: Settings }
          ].map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-[#3F513D] text-[#FAF8F5] shadow-sm'
                    : 'text-[#556153] hover:text-[#2C352B] hover:bg-[#EFECE6]'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{item.label}</span>
                {item.badge > 0 && (
                  <span
                    className={`ml-1 px-1.5 py-0.2 text-[10px] rounded-full font-mono ${
                      isActive ? 'bg-[#2D3A2C] text-[#FAF8F5]' : 'bg-[#E5E0D8] text-[#556153]'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* API Drawer Trigger */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsLogDrawerOpen(!isLogDrawerOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#FAF8F5] border border-[#E5E0D8] text-xs font-medium text-[#3F513D] hover:bg-[#EFECE6] transition"
          >
            <Terminal className="w-3.5 h-3.5 text-[#3F513D]" />
            <span className="hidden sm:inline">API Logs</span>
            <span className="bg-[#E2EBDD] px-1.5 py-0.5 rounded text-[10px] text-[#2D3A2C] font-mono">{logs.length}</span>
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-4 lg:p-8 max-w-7xl w-full mx-auto pb-24">
        {/* DASHBOARD TAB */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white border border-[#E5E0D8] rounded-xl p-4 shadow-sm">
                <div className="flex items-center justify-between text-[#6B7569] mb-1">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Connected Accounts</span>
                  <Key className="w-4 h-4 text-[#3F513D]" />
                </div>
                <div className="text-2xl font-bold text-[#2C352B]">{stats.connectedCount} / 2</div>
                <div className="text-[11px] text-[#6B7569] mt-0.5">LinkedIn & Reddit Vault</div>
              </div>

              <div className="bg-white border border-[#E5E0D8] rounded-xl p-4 shadow-sm">
                <div className="flex items-center justify-between text-[#6B7569] mb-1">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Scheduled Queue</span>
                  <Calendar className="w-4 h-4 text-[#8C6B2A]" />
                </div>
                <div className="text-2xl font-bold text-[#2C352B]">{stats.scheduledCount}</div>
                <div className="text-[11px] text-[#6B7569] mt-0.5">Auto-Publish (7-Day Limit)</div>
              </div>

              <div className="bg-white border border-[#E5E0D8] rounded-xl p-4 shadow-sm">
                <div className="flex items-center justify-between text-[#6B7569] mb-1">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Total Published</span>
                  <Send className="w-4 h-4 text-[#2E542B]" />
                </div>
                <div className="text-2xl font-bold text-[#2C352B]">{stats.publishedCount}</div>
                <div className="text-[11px] text-[#6B7569] mt-0.5">Published Live</div>
              </div>

              <div className="bg-white border border-[#E5E0D8] rounded-xl p-4 shadow-sm">
                <div className="flex items-center justify-between text-[#6B7569] mb-1">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Drafts In Pipeline</span>
                  <FileText className="w-4 h-4 text-[#556153]" />
                </div>
                <div className="text-2xl font-bold text-[#2C352B]">{stats.draftCount}</div>
                <div className="text-[11px] text-[#6B7569] mt-0.5">Requires Client Review</div>
              </div>
            </div>

            {/* Missed Posts Stale Banner */}
            {stats.missedCount > 0 && (
              <div className="bg-[#FEF6E7] border border-[#E8D4A8] rounded-xl p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <AlertTriangle className="w-5 h-5 text-[#8C6B2A]" />
                  <div>
                    <h4 className="text-xs font-bold text-[#8C6B2A]">Missed Scheduled Posts Detected ({stats.missedCount})</h4>
                    <p className="text-[11px] text-[#7A5B20]">
                      The application was offline when the scheduled dispatch time passed (&gt;2 hours ago). Review and publish manually or reschedule.
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => { setFilterStatus('missed'); setActiveTab('posts'); }}
                  className="px-3 py-1.5 rounded-lg text-xs font-bold bg-[#8C6B2A] text-white hover:bg-[#72541C] transition"
                >
                  Review Missed Posts
                </button>
              </div>
            )}

            {/* Account Status Grid */}
            <div className="grid md:grid-cols-2 gap-6">
              <div className="bg-white border border-[#E5E0D8] rounded-xl p-5 shadow-sm">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="font-bold text-sm text-[#2C352B]">LinkedIn Integration</h3>
                    <p className="text-[11px] text-[#6B7569]">Destination: Member UGC Feed</p>
                  </div>
                  {accounts.linkedin.connected ? (
                    <span className="px-2.5 py-1 bg-[#E2EBDD] text-[#2E542B] border border-[#B2C9B0] rounded-full text-xs font-semibold">
                      Connected
                    </span>
                  ) : (
                    <span className="px-2.5 py-1 bg-[#E5E0D8] text-[#6B7569] rounded-full text-xs font-medium">
                      Not Connected
                    </span>
                  )}
                </div>
                <p className="text-xs text-[#556153] mb-4 leading-relaxed">
                  Automated scheduling and direct publishing to LinkedIn feeds with rate limit protection and backoff.
                </p>
                {accounts.linkedin.connected && accounts.linkedin.daysRemaining > 0 && (
                  <div className={`text-[11px] mb-3 px-3 py-1.5 rounded-lg border flex items-center gap-2 ${
                    accounts.linkedin.expiresSoon ? 'bg-[#FEF6E7] border-[#E8D4A8] text-[#8C6B2A]' : 'bg-[#F2F6F1] border-[#B2C9B0] text-[#2E542B]'
                  }`}>
                    <Clock className="w-3.5 h-3.5" />
                    <span>OAuth token active (expires in ~{accounts.linkedin.daysRemaining} days)</span>
                  </div>
                )}
                <div className="flex items-center justify-between pt-3 border-t border-[#E5E0D8]">
                  <span className="text-xs text-[#6B7569]">{accounts.linkedin.connected ? accounts.linkedin.accountName : 'Pre-configured Shared OAuth'}</span>
                  {accounts.linkedin.connected ? (
                    <button
                      onClick={() => handleDisconnect('linkedin')}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#FAF8F5] border border-[#E5E0D8] text-[#8C2A2A] hover:bg-[#FDF2F2] transition"
                    >
                      Disconnect
                    </button>
                  ) : (
                    <button
                      onClick={() => handleConnect('linkedin')}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#0A66C2] text-white hover:bg-[#084e96] transition flex items-center gap-1.5 shadow-sm"
                    >
                      <ExternalLink className="w-3.5 h-3.5" /> Connect LinkedIn
                    </button>
                  )}
                </div>
              </div>

              <div className="bg-white border border-[#E5E0D8] rounded-xl p-5 shadow-sm">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="font-bold text-sm text-[#2C352B]">Reddit Integration</h3>
                    <p className="text-[11px] text-[#6B7569]">Destination: Subreddit Community Discussions</p>
                  </div>
                  {accounts.reddit.connected ? (
                    <span className="px-2.5 py-1 bg-[#E2EBDD] text-[#2E542B] border border-[#B2C9B0] rounded-full text-xs font-semibold">
                      Connected
                    </span>
                  ) : (
                    <span className="px-2.5 py-1 bg-[#E5E0D8] text-[#6B7569] rounded-full text-xs font-medium">
                      Not Connected
                    </span>
                  )}
                </div>
                <p className="text-xs text-[#556153] mb-4 leading-relaxed">
                  Submits authentic discussions directly to target subreddits with duplicate content checking to protect your account.
                </p>
                {accounts.reddit.connected && (
                  <div className="text-[11px] mb-3 px-3 py-1.5 rounded-lg border bg-[#F2F6F1] border-[#B2C9B0] text-[#2E542B] flex items-center gap-2">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Permanent token active in Windows Credential Vault</span>
                  </div>
                )}
                <div className="flex items-center justify-between pt-3 border-t border-[#E5E0D8]">
                  <span className="text-xs text-[#6B7569]">{accounts.reddit.connected ? accounts.reddit.accountName : 'Pre-configured Shared OAuth'}</span>
                  {accounts.reddit.connected ? (
                    <button
                      onClick={() => handleDisconnect('reddit')}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#FAF8F5] border border-[#E5E0D8] text-[#8C2A2A] hover:bg-[#FDF2F2] transition"
                    >
                      Disconnect
                    </button>
                  ) : (
                    <button
                      onClick={() => handleConnect('reddit')}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#FF4500] text-white hover:bg-[#e03d00] transition flex items-center gap-1.5 shadow-sm"
                    >
                      <ExternalLink className="w-3.5 h-3.5" /> Connect Reddit
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* CREATE POST TAB */}
        {activeTab === 'create' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between bg-white p-4 rounded-xl border border-[#E5E0D8]">
              <div>
                <h2 className="text-base font-bold text-[#2C352B]">Content Strategy & Draft Generator</h2>
                <p className="text-xs text-[#6B7569]">Single-API generation for scroll-stopping LinkedIn hooks and authentic Reddit discussions.</p>
              </div>
              <button
                onClick={handleGenerateContent}
                disabled={isGenerating}
                className="bg-[#3F513D] hover:bg-[#2D3A2C] text-[#FAF8F5] px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition disabled:opacity-50 shadow-sm"
              >
                {isGenerating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                {generatedContent.linkedin ? 'Regenerate Drafts' : 'Generate Content'}
              </button>
            </div>

            {/* Inputs Grid */}
            <div className="grid md:grid-cols-3 gap-4 bg-white border border-[#E5E0D8] rounded-xl p-5">
              <div>
                <label className="text-xs font-semibold text-[#2C352B] block mb-1">Topic / Core Subject</label>
                <input
                  type="text"
                  maxLength={500}
                  placeholder="e.g. AI automation in small business operations"
                  value={genForm.topic}
                  onChange={(e) => setGenForm({ ...genForm, topic: e.target.value })}
                  className="w-full bg-[#FAF8F5] border border-[#E5E0D8] rounded-lg px-3 py-2 text-xs text-[#2C352B] focus:outline-none focus:border-[#3F513D]"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-[#2C352B] block mb-1">Main Value Proposition</label>
                <input
                  type="text"
                  maxLength={2000}
                  placeholder="e.g. Automated response workflows cut turnaround times by 80%"
                  value={genForm.mainMessage}
                  onChange={(e) => setGenForm({ ...genForm, mainMessage: e.target.value })}
                  className="w-full bg-[#FAF8F5] border border-[#E5E0D8] rounded-lg px-3 py-2 text-xs text-[#2C352B] focus:outline-none focus:border-[#3F513D]"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-[#2C352B] block mb-1">Target Audience</label>
                <input
                  type="text"
                  maxLength={500}
                  placeholder="e.g. Founders & Operations Managers"
                  value={genForm.targetAudience}
                  onChange={(e) => setGenForm({ ...genForm, targetAudience: e.target.value })}
                  className="w-full bg-[#FAF8F5] border border-[#E5E0D8] rounded-lg px-3 py-2 text-xs text-[#2C352B] focus:outline-none focus:border-[#3F513D]"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-[#2C352B] block mb-1">Tone of Voice</label>
                <select
                  value={genForm.tone}
                  onChange={(e) => setGenForm({ ...genForm, tone: e.target.value })}
                  className="w-full bg-[#FAF8F5] border border-[#E5E0D8] rounded-lg px-3 py-2 text-xs text-[#2C352B] focus:outline-none focus:border-[#3F513D]"
                >
                  <option value="Thought Leadership">Thought Leadership</option>
                  <option value="Conversational">Conversational</option>
                  <option value="Direct & Technical">Direct & Technical</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-[#2C352B] block mb-1">Target Subreddit</label>
                <input
                  type="text"
                  value={genForm.subreddit}
                  onChange={(e) => setGenForm({ ...genForm, subreddit: e.target.value })}
                  className="w-full bg-[#FAF8F5] border border-[#E5E0D8] rounded-lg px-3 py-2 text-xs text-[#2C352B] focus:outline-none focus:border-[#3F513D]"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-[#2C352B] block mb-1">Call to Action Link (Optional)</label>
                <input
                  type="url"
                  placeholder="https://example.com/demo"
                  value={genForm.websiteUrl}
                  onChange={(e) => setGenForm({ ...genForm, websiteUrl: e.target.value })}
                  className="w-full bg-[#FAF8F5] border border-[#E5E0D8] rounded-lg px-3 py-2 text-xs text-[#2C352B] focus:outline-none focus:border-[#3F513D]"
                />
              </div>

              <div className="md:col-span-3">
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-[#2C352B] flex items-center gap-1.5">
                    <span>Reference Post / Inspiration (Optional)</span>
                    <span className="text-[10px] text-[#8C7A6B] bg-[#F4EFEA] px-2 py-0.5 rounded font-normal">Optional</span>
                  </label>
                  <span className="text-[11px] text-[#6B7569]">Paste a sample post or format for the AI to emulate style/tone</span>
                </div>
                <textarea
                  rows={3}
                  maxLength={4000}
                  placeholder="Paste a viral post, hook, or outline you want the AI to analyze and model the content structure after (optional)..."
                  value={genForm.referencePost}
                  onChange={(e) => setGenForm({ ...genForm, referencePost: e.target.value })}
                  className="w-full bg-[#FAF8F5] border border-[#E5E0D8] rounded-lg px-3 py-2 text-xs text-[#2C352B] focus:outline-none focus:border-[#3F513D] resize-y"
                />
              </div>
            </div>

            {/* Generated Outputs Preview Grid */}
            <div className="grid md:grid-cols-2 gap-6">
              {/* LinkedIn Draft */}
              <div className="bg-white border border-[#E5E0D8] rounded-xl p-5 shadow-sm space-y-3 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between pb-2 border-b border-[#E5E0D8]">
                    <span className="font-bold text-xs text-[#2C352B] flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-[#0A66C2]"></span> LinkedIn Native Draft
                    </span>
                    <span className="text-[10px] text-[#6B7569]">Hook + Formatted Body + 3-5 Hashtags</span>
                  </div>
                  <textarea
                    rows={12}
                    value={generatedContent.linkedin}
                    onChange={(e) => setGeneratedContent({ ...generatedContent, linkedin: e.target.value })}
                    placeholder="Click 'Generate Content' to create platform-optimized LinkedIn draft..."
                    className="w-full bg-[#FAF8F5] border border-[#E5E0D8] rounded-lg p-3 text-xs text-[#2C352B] leading-relaxed resize-none mt-2 font-sans"
                  />
                </div>
                <div className="grid grid-cols-3 gap-2 pt-2 border-t border-[#E5E0D8]">
                  <button
                    onClick={() => saveDraft('linkedin', generatedContent.linkedin)}
                    disabled={!generatedContent.linkedin}
                    className="py-2 px-2.5 bg-[#FAF8F5] border border-[#E5E0D8] hover:bg-[#EFECE6] text-xs font-semibold rounded-lg text-[#2C352B] transition disabled:opacity-40"
                  >
                    Save Draft
                  </button>
                  <button
                    onClick={() =>
                      publishNow({
                        platform: 'linkedin',
                        content: generatedContent.linkedin,
                        topic: genForm.topic,
                        destination: 'Personal Profile (Feed)'
                      })
                    }
                    disabled={!generatedContent.linkedin || isPublishing}
                    className="py-2 px-2.5 bg-[#FAF8F5] border border-[#3F513D]/40 text-[#2E542B] hover:bg-[#E2EBDD] text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition disabled:opacity-40"
                  >
                    <Send className="w-3.5 h-3.5" /> Publish Now
                  </button>
                  <button
                    onClick={() => openScheduleModal('linkedin', generatedContent.linkedin)}
                    disabled={!generatedContent.linkedin}
                    className="py-2 px-2.5 bg-[#3F513D] hover:bg-[#2D3A2C] text-white text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition disabled:opacity-40 shadow-sm"
                  >
                    <Calendar className="w-3.5 h-3.5" /> Schedule
                  </button>
                </div>
              </div>

              {/* Reddit Draft */}
              <div className="bg-white border border-[#E5E0D8] rounded-xl p-5 shadow-sm space-y-3 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between pb-2 border-b border-[#E5E0D8]">
                    <span className="font-bold text-xs text-[#2C352B] flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-[#FF4500]"></span> Reddit Community Discussion
                    </span>
                    <span className="text-[10px] text-[#6B7569]">Authentic Title + Value Markdown</span>
                  </div>
                  <textarea
                    rows={12}
                    value={generatedContent.reddit}
                    onChange={(e) => setGeneratedContent({ ...generatedContent, reddit: e.target.value })}
                    placeholder="Click 'Generate Content' to create genuine Reddit discussion without marketing fluff..."
                    className="w-full bg-[#FAF8F5] border border-[#E5E0D8] rounded-lg p-3 text-xs text-[#2C352B] leading-relaxed resize-none mt-2 font-mono text-[11px]"
                  />
                </div>
                <div className="grid grid-cols-3 gap-2 pt-2 border-t border-[#E5E0D8]">
                  <button
                    onClick={() => saveDraft('reddit', generatedContent.reddit, genForm.subreddit || 'r/smallbusiness')}
                    disabled={!generatedContent.reddit}
                    className="py-2 px-2.5 bg-[#FAF8F5] border border-[#E5E0D8] hover:bg-[#EFECE6] text-xs font-semibold rounded-lg text-[#2C352B] transition disabled:opacity-40"
                  >
                    Save Draft
                  </button>
                  <button
                    onClick={() =>
                      publishNow({
                        platform: 'reddit',
                        content: generatedContent.reddit,
                        topic: genForm.topic,
                        destination: genForm.subreddit || 'r/smallbusiness'
                      })
                    }
                    disabled={!generatedContent.reddit || isPublishing}
                    className="py-2 px-2.5 bg-[#FAF8F5] border border-[#3F513D]/40 text-[#2E542B] hover:bg-[#E2EBDD] text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition disabled:opacity-40"
                  >
                    <Send className="w-3.5 h-3.5" /> Publish Now
                  </button>
                  <button
                    onClick={() => openScheduleModal('reddit', generatedContent.reddit)}
                    disabled={!generatedContent.reddit}
                    className="py-2 px-2.5 bg-[#3F513D] hover:bg-[#2D3A2C] text-white text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition disabled:opacity-40 shadow-sm"
                  >
                    <Calendar className="w-3.5 h-3.5" /> Schedule
                  </button>
                </div>
              </div>
            </div>

            {/* Bulk Action Bar */}
            <div className="flex items-center justify-between bg-white border border-[#E5E0D8] p-4 rounded-xl">
              <span className="text-xs text-[#6B7569]">
                Client review is always required before automatic execution (7-day schedule window).
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => openScheduleModal('both')}
                  disabled={!generatedContent.linkedin && !generatedContent.reddit}
                  className="px-4 py-2 bg-[#3F513D] hover:bg-[#2D3A2C] text-white text-xs font-semibold rounded-lg flex items-center gap-2 transition disabled:opacity-40 shadow-sm"
                >
                  <Calendar className="w-4 h-4" /> Schedule Both Posts
                </button>
              </div>
            </div>
          </div>
        )}

        {/* POSTS REPOSITORY TAB */}
        {activeTab === 'posts' && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded-xl border border-[#E5E0D8]">
              <div>
                <h2 className="text-base font-bold text-[#2C352B]">Content Repository</h2>
                <p className="text-xs text-[#6B7569]">Manage all drafts, scheduled posts, published posts, and cancellations.</p>
              </div>

              {/* Status Filter Tabs */}
              <div className="flex items-center gap-1 bg-[#FAF8F5] p-1 rounded-lg border border-[#E5E0D8] overflow-x-auto">
                {['all', 'draft', 'scheduled', 'missed', 'published', 'cancelled', 'failed'].map((st) => (
                  <button
                    key={st}
                    onClick={() => setFilterStatus(st)}
                    className={`px-3 py-1 text-xs rounded font-medium capitalize transition whitespace-nowrap ${
                      filterStatus === st ? 'bg-[#3F513D] text-[#FAF8F5]' : 'text-[#556153] hover:bg-[#EFECE6]'
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-3">
              {filteredPosts.length === 0 ? (
                <div className="bg-white border border-[#E5E0D8] p-8 text-center text-xs text-[#6B7569] rounded-xl">
                  No posts recorded in database. Generate drafts or schedule content to begin.
                </div>
              ) : (
                filteredPosts.map((post) => (
                  <div key={post.id} className="bg-white border border-[#E5E0D8] rounded-xl p-4 space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="px-2 py-0.5 bg-[#E2EBDD] text-[#3F513D] font-bold text-[10px] uppercase rounded">
                          {post.platform}
                        </span>
                        <span className="text-xs font-mono bg-[#FAF8F5] px-2 py-0.5 border border-[#E5E0D8] rounded text-[#556153]">
                          {post.destination || post.subreddit || (post.platform === 'linkedin' ? 'Personal Profile' : 'Subreddit')}
                        </span>
                        <span className="text-xs font-semibold text-[#2C352B]">{post.topic}</span>
                      </div>

                      <div className="flex items-center gap-2">
                        <span
                          className={`text-[11px] font-bold uppercase px-2 py-0.5 rounded border ${
                            post.status === 'published'
                              ? 'bg-[#E2EBDD] text-[#2E542B] border-[#B2C9B0]'
                              : post.status === 'scheduled'
                              ? 'bg-[#FEF6E7] text-[#8C6B2A] border-[#E8D4A8]'
                              : post.status === 'missed'
                              ? 'bg-[#FEF6E7] text-[#B45309] border-[#FCD34D]'
                              : post.status === 'failed'
                              ? 'bg-[#FDF2F2] text-[#8C2A2A] border-[#E5B8B8]'
                              : post.status === 'cancelled'
                              ? 'bg-[#F0F2F0] text-[#6B7569] border-[#D0D4D0]'
                              : 'bg-[#FAF8F5] text-[#556153] border-[#E5E0D8]'
                          }`}
                        >
                          {post.status}
                        </span>
                        {post.status === 'published' && post.externalId && (
                          <span className="text-[10px] text-[#6B7569] font-mono bg-[#FAF8F5] px-2 py-0.5 rounded border border-[#E5E0D8]">
                            ID: {post.externalId.slice(-10)}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="text-xs text-[#2C352B] bg-[#FAF8F5] border border-[#E5E0D8]/60 p-3 rounded-lg whitespace-pre-wrap max-h-36 overflow-y-auto font-sans leading-relaxed">
                      {post.content}
                    </div>

                    {post.errorMessage && (
                      <div className="text-[11px] text-[#8C2A2A] bg-[#FDF2F2] border border-[#E5B8B8] p-2 rounded-lg flex items-center gap-2">
                        <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                        <span>{post.errorMessage}</span>
                      </div>
                    )}

                    <div className="flex flex-wrap items-center justify-between pt-2 border-t border-[#E5E0D8]/60 text-xs gap-3">
                      <div className="flex items-center gap-3 text-[11px] text-[#6B7569]">
                        {post.scheduledAt && (
                          <span className="flex items-center gap-1 font-medium text-[#2C352B]">
                            <Clock className="w-3.5 h-3.5 text-[#3F513D]" />
                            Execution: <strong>{formatScheduledTime(post.scheduledAt)}</strong>
                          </span>
                        )}
                        {post.publishedAt && (
                          <span>Published on: <strong>{formatScheduledTime(post.publishedAt)}</strong></span>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        {post.status === 'missed' && (
                          <button
                            onClick={() => publishNow(post)}
                            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#8C6B2A] text-white hover:bg-[#72541C] transition flex items-center gap-1"
                          >
                            <Send className="w-3.5 h-3.5" /> Publish Missed Post Now
                          </button>
                        )}
                        {post.status === 'draft' && (
                          <>
                            <button
                              onClick={() => openScheduleModal(post.platform, post.content, post)}
                              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#FAF8F5] border border-[#E5E0D8] hover:bg-[#EFECE6] text-[#2C352B] transition flex items-center gap-1"
                            >
                              <Calendar className="w-3.5 h-3.5" /> Schedule
                            </button>
                            <button
                              onClick={() => publishNow(post)}
                              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#E2EBDD] text-[#2E542B] hover:bg-[#C3D4BC] transition flex items-center gap-1"
                            >
                              <Send className="w-3.5 h-3.5" /> Publish Now
                            </button>
                          </>
                        )}
                        {post.status === 'scheduled' && (
                          <>
                            <button
                              onClick={() => openEditModal(post)}
                              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#FAF8F5] border border-[#E5E0D8] hover:bg-[#EFECE6] text-[#2C352B] transition flex items-center gap-1"
                            >
                              <Edit3 className="w-3.5 h-3.5 text-[#3F513D]" /> Edit Time
                            </button>
                            <button
                              onClick={() => publishNow(post)}
                              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#E2EBDD] text-[#2E542B] hover:bg-[#C3D4BC] transition flex items-center gap-1"
                            >
                              <Send className="w-3.5 h-3.5" /> Publish Now
                            </button>
                            <button
                              onClick={() => cancelScheduledPost(post.id)}
                              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#FAF8F5] border border-[#E5E0D8] text-[#8C2A2A] hover:bg-[#FDF2F2] transition"
                            >
                              Cancel
                            </button>
                          </>
                        )}
                        <button
                          onClick={() => deletePost(post.id)}
                          className="p-1.5 text-[#6B7569] hover:text-[#8C2A2A] rounded transition"
                          title="Delete Post"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* SCHEDULED QUEUE TAB */}
        {activeTab === 'schedule' && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded-xl border border-[#E5E0D8]">
              <div>
                <h2 className="text-base font-bold text-[#2C352B]">Scheduled Autonomous Queue</h2>
                <p className="text-xs text-[#6B7569]">All approved posts set for automated background dispatch within 7 days.</p>
              </div>
              <button
                onClick={() => openScheduleModal('linkedin')}
                className="px-3.5 py-2 rounded-lg text-xs font-semibold bg-[#3F513D] hover:bg-[#2D3A2C] text-white transition flex items-center gap-1.5 self-start sm:self-auto"
              >
                <Calendar className="w-3.5 h-3.5" /> Schedule New Post
              </button>
            </div>

            <div className="space-y-3">
              {scheduledPosts.length === 0 ? (
                <div className="bg-white border border-[#E5E0D8] p-12 text-center rounded-xl space-y-2">
                  <Clock className="w-8 h-8 text-[#6B7569] mx-auto opacity-40" />
                  <p className="text-xs font-semibold text-[#2C352B]">Queue is Empty</p>
                  <p className="text-[11px] text-[#6B7569]">
                    Draft posts can be scheduled with explicit confirmation for hands-off publishing.
                  </p>
                </div>
              ) : (
                scheduledPosts.map((post) => (
                  <div key={post.id} className="bg-white border border-[#E5E0D8] rounded-xl p-4 space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="px-2 py-0.5 bg-[#E2EBDD] text-[#3F513D] font-bold text-[10px] uppercase rounded">
                          {post.platform}
                        </span>
                        <span className="text-xs font-semibold text-[#2C352B]">{post.topic}</span>
                        <span className="text-xs font-mono bg-[#FAF8F5] px-2 py-0.5 border border-[#E5E0D8] rounded text-[#556153]">
                          {post.destination || post.subreddit || (post.platform === 'linkedin' ? 'Personal Profile' : 'Subreddit')}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        {post.status === 'missed' ? (
                          <span className="text-[11px] font-bold uppercase px-2 py-0.5 rounded bg-[#FEF6E7] text-[#B45309] border border-[#FCD34D]">
                            Missed Scheduled Time
                          </span>
                        ) : (
                          <span className="text-[11px] font-bold uppercase px-2 py-0.5 rounded bg-[#FEF6E7] text-[#8C6B2A] border border-[#E8D4A8]">
                            {getRelativeTimeBadge(post.scheduledAt)}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="text-xs text-[#2C352B] bg-[#FAF8F5] border border-[#E5E0D8]/60 p-3 rounded-lg whitespace-pre-wrap max-h-36 overflow-y-auto font-sans leading-relaxed">
                      {post.content}
                    </div>

                    <div className="flex flex-wrap items-center justify-between pt-2 border-t border-[#E5E0D8]/60 text-xs gap-3">
                      <div className="flex items-center gap-3 text-[11px] text-[#6B7569]">
                        <span className="flex items-center gap-1 font-medium text-[#2C352B]">
                          <Clock className="w-3.5 h-3.5 text-[#3F513D]" />
                          Automatic Publish: <strong>{formatScheduledTime(post.scheduledAt)}</strong>
                        </span>
                        <span>•</span>
                        <span>Timezone: <strong>{post.timezone || userTimezone}</strong></span>
                      </div>

                      <div className="flex items-center gap-2">
                        {post.status === 'missed' ? (
                          <button
                            onClick={() => publishNow(post)}
                            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#8C6B2A] text-white hover:bg-[#72541C] transition flex items-center gap-1"
                          >
                            <Send className="w-3.5 h-3.5" /> Publish Missed Post Now
                          </button>
                        ) : (
                          <>
                            <button
                              onClick={() => openEditModal(post)}
                              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#FAF8F5] border border-[#E5E0D8] hover:bg-[#EFECE6] text-[#2C352B] transition flex items-center gap-1"
                            >
                              <Edit3 className="w-3.5 h-3.5 text-[#3F513D]" /> Edit Content & Time
                            </button>
                            <button
                              onClick={() => publishNow(post)}
                              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#E2EBDD] text-[#2E542B] hover:bg-[#C3D4BC] transition flex items-center gap-1"
                            >
                              <Send className="w-3.5 h-3.5" /> Publish Now
                            </button>
                            <button
                              onClick={() => cancelScheduledPost(post.id)}
                              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#FAF8F5] border border-[#E5E0D8] text-[#8C2A2A] hover:bg-[#FDF2F2] transition"
                            >
                              Cancel
                            </button>
                          </>
                        )}
                        <button
                          onClick={() => deletePost(post.id)}
                          className="p-1.5 text-[#6B7569] hover:text-[#8C2A2A] rounded transition"
                          title="Delete Post"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* SETTINGS & INTEGRATIONS TAB */}
        {activeTab === 'settings' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between bg-white p-4 rounded-xl border border-[#E5E0D8]">
              <div>
                <h2 className="text-base font-bold text-[#2C352B]">Integrations, Credentials & Security</h2>
                <p className="text-xs text-[#6B7569]">
                  All client secrets and OAuth tokens are stored encrypted using Windows Credential Manager (DPAPI). Never stored in plaintext.
                </p>
              </div>
              <button
                onClick={handleSaveIntegrations}
                disabled={isSavingSettings}
                className="bg-[#3F513D] hover:bg-[#2D3A2C] text-[#FAF8F5] px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition shadow-sm"
              >
                {isSavingSettings ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Lock className="w-3.5 h-3.5" />}
                Save All Credentials
              </button>
            </div>

            {/* AI Engine Configuration */}
            <div className="bg-white border border-[#E5E0D8] rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#E5E0D8]">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-[#3F513D]" />
                  <h3 className="font-bold text-sm text-[#2C352B]">AI Generation Engine (Groq API)</h3>
                </div>
                <span className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${
                  integrations.groq.configured ? 'bg-[#E2EBDD] text-[#2E542B] border-[#B2C9B0]' : 'bg-[#FEF6E7] text-[#8C6B2A] border-[#E8D4A8]'
                }`}>
                  {integrations.groq.configured ? `Active (${integrations.groq.masked})` : 'Key Not Configured'}
                </span>
              </div>
              <p className="text-xs text-[#556153] leading-relaxed">
                Provide your dedicated Groq API Key to enable instant dual-platform draft generation. Your key is stored strictly encrypted in the Windows Credential Vault.
              </p>
              <div className="max-w-xl">
                <label className="text-xs font-semibold text-[#2C352B] block mb-1">Groq API Key</label>
                <div className="flex gap-2">
                  <input
                    type="password"
                    placeholder={integrations.groq.configured ? `Stored (${integrations.groq.masked}) - enter new to replace` : "gsk_..."}
                    value={integrationForm.groq_api_key}
                    onChange={(e) => setIntegrationForm({ ...integrationForm, groq_api_key: e.target.value })}
                    className="flex-1 bg-[#FAF8F5] border border-[#E5E0D8] rounded-lg px-3 py-2 text-xs text-[#2C352B] font-mono focus:outline-none focus:border-[#3F513D]"
                  />
                  <button
                    onClick={handleSaveIntegrations}
                    disabled={!integrationForm.groq_api_key.trim()}
                    className="px-3.5 py-2 bg-[#FAF8F5] border border-[#E5E0D8] hover:bg-[#EFECE6] text-xs font-semibold rounded-lg disabled:opacity-40"
                  >
                    Save Key
                  </button>
                </div>
              </div>
            </div>

            {/* LinkedIn Integration Panel */}
            <div className="bg-white border border-[#E5E0D8] rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#E5E0D8]">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#0A66C2]"></span>
                  <h3 className="font-bold text-sm text-[#2C352B]">LinkedIn Integration</h3>
                  {integrations.linkedin.shared_oauth ? (
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-[#E2EBDD] text-[#2E542B] border border-[#B2C9B0]">
                      Shared App Ready
                    </span>
                  ) : (
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-[#FEF6E7] text-[#8C6B2A] border border-[#E8D4A8]">
                      Custom App Active ({integrations.linkedin.client_id_masked})
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {accounts.linkedin.connected ? (
                    <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-[#E2EBDD] text-[#2E542B] border border-[#B2C9B0]">
                      Connected: {accounts.linkedin.accountName}
                    </span>
                  ) : (
                    <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-[#E5E0D8] text-[#6B7569]">
                      Not Connected
                    </span>
                  )}
                </div>
              </div>

              {/* Token Expiry Warning */}
              {accounts.linkedin.connected && accounts.linkedin.expiresSoon && (
                <div className="bg-[#FEF6E7] border border-[#E8D4A8] rounded-lg p-3 text-xs text-[#8C6B2A] flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    <span>LinkedIn OAuth token expires in ~{accounts.linkedin.daysRemaining} days. Reconnect to renew 60-day token window.</span>
                  </div>
                  <button
                    onClick={() => handleConnect('linkedin')}
                    className="px-2.5 py-1 bg-[#8C6B2A] text-white rounded text-xs font-semibold"
                  >
                    Reconnect Now
                  </button>
                </div>
              )}

              {/* Custom App Notice & Quick Revert */}
              {integrations.linkedin.has_custom_credentials && (
                <div className="bg-[#FEF6E7] border border-[#E8D4A8] rounded-lg p-3 text-xs text-[#8C6B2A] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                  <div>
                    <span className="font-bold flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-[#8C6B2A] shrink-0" />
                      Custom Developer App Active: {integrations.linkedin.client_id_masked}
                    </span>
                    <p className="text-[11px] text-[#71541D] mt-0.5">
                      If you see &quot;The redirect_uri does not match the registered value&quot;, your LinkedIn Developer App requires the exact redirect URL below. Alternatively, click &quot;Revert to Shared App&quot; to connect immediately without entering credentials.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleResetToShared('linkedin')}
                    className="px-3 py-1.5 bg-[#8C6B2A] hover:bg-[#73531b] text-white rounded-lg text-xs font-semibold whitespace-nowrap shadow-sm"
                  >
                    ↺ Revert to Shared App
                  </button>
                </div>
              )}

              {/* Shared OAuth Status Banner */}
              <div className="bg-[#F4F7F4] border border-[#D3E1D2] rounded-lg p-4 space-y-2 text-xs text-[#334631]">
                <div className="font-bold text-[#233821] flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-[#2E542B]" />
                  {integrations.linkedin.shared_oauth ? "Centralized Shared OAuth Ready:" : "Direct Authorization Available:"}
                </div>
                <p className="text-[11px] leading-relaxed">
                  {integrations.linkedin.shared_oauth
                    ? "LinkedIn developer credentials are configured centrally on the secure backend. No developer app setup or client secrets needed. Simply click below to authorize."
                    : "You are currently running with custom developer credentials. Click Connect below or expand Advanced to manage redirect URIs."}
                </p>
                <div className="flex items-center gap-3 pt-1">
                  {accounts.linkedin.connected ? (
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleConnect('linkedin')}
                        className="px-3.5 py-1.5 bg-[#0A66C2] hover:bg-[#084e96] text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-sm"
                      >
                        <RefreshCw className="w-3.5 h-3.5" /> Reconnect / Switch Profile
                      </button>
                      <button
                        onClick={() => handleDisconnect('linkedin')}
                        className="px-3 py-1.5 bg-white border border-[#E5E0D8] text-[#8C2A2A] hover:bg-[#FDF2F2] rounded-lg text-xs font-semibold"
                      >
                        Disconnect
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => handleConnect('linkedin')}
                      className="px-4 py-2 bg-[#0A66C2] hover:bg-[#084e96] text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-sm"
                    >
                      <ExternalLink className="w-3.5 h-3.5" /> Connect LinkedIn Account
                    </button>
                  )}
                  <span className="text-[11px] text-[#6B7569]">Scopes: <code>openid profile w_member_social</code></span>
                </div>
              </div>

              {/* Advanced Custom Credentials Accordion */}
              <div className="pt-1">
                <button
                  type="button"
                  onClick={() => setShowCustomLi(!showCustomLi)}
                  className="text-xs text-[#556153] hover:text-[#2C352B] font-semibold flex items-center gap-1"
                >
                  <span>{showCustomLi ? '▼ Hide' : '▶ Show'} Custom Developer Credentials (Advanced & Redirect URI Settings)</span>
                </button>

                {showCustomLi && (
                  <div className="mt-3 p-4 bg-[#FAF8F5] border border-[#E5E0D8] rounded-lg space-y-4">
                    {/* Step-by-Step Redirect URI Guide */}
                    <div className="p-3 bg-white border border-[#E5E0D8] rounded-lg space-y-2">
                      <div className="font-bold text-xs text-[#2C352B] flex items-center gap-1.5">
                        <Info className="w-4 h-4 text-[#0A66C2]" /> LinkedIn Developer Portal Redirect URI Registration:
                      </div>
                      <p className="text-[11px] text-[#6B7569] leading-relaxed">
                        To resolve <em>&quot;The redirect_uri does not match the registered value&quot;</em>, log into{' '}
                        <a href="https://www.linkedin.com/developers/apps" target="_blank" rel="noreferrer" className="text-[#0A66C2] underline font-semibold">
                          LinkedIn Developer Portal
                        </a>
                        , select your app, open the <strong>Auth</strong> tab, and paste the exact URL below into <strong>Authorized redirect URLs for your app</strong>:
                      </p>
                      <div className="space-y-1.5 pt-1">
                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            readOnly
                            value="http://127.0.0.1:8000/auth/linkedin/callback"
                            className="flex-1 bg-[#F3EFEA] border border-[#E5E0D8] rounded px-2.5 py-1 text-[11px] font-mono text-[#2C352B] select-all"
                          />
                          <button
                            type="button"
                            onClick={() => copyToClipboard('http://127.0.0.1:8000/auth/linkedin/callback')}
                            className="px-2.5 py-1 bg-white border border-[#E5E0D8] hover:bg-[#EFECE6] rounded text-[11px] font-semibold flex items-center gap-1"
                          >
                            <Copy className="w-3 h-3" /> Copy 127.0.0.1 (Recommended)
                          </button>
                        </div>
                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            readOnly
                            value="http://localhost:8000/auth/linkedin/callback"
                            className="flex-1 bg-[#F3EFEA] border border-[#E5E0D8] rounded px-2.5 py-1 text-[11px] font-mono text-[#2C352B] select-all"
                          />
                          <button
                            type="button"
                            onClick={() => copyToClipboard('http://localhost:8000/auth/linkedin/callback')}
                            className="px-2.5 py-1 bg-white border border-[#E5E0D8] hover:bg-[#EFECE6] rounded text-[11px] font-semibold flex items-center gap-1"
                          >
                            <Copy className="w-3 h-3" /> Copy localhost
                          </button>
                        </div>
                      </div>
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-[#2C352B] block mb-1">Active Redirect URI used by AutoSocial Poster:</label>
                      <div className="flex flex-col sm:flex-row gap-2">
                        <input
                          type="text"
                          placeholder="http://127.0.0.1:8000/auth/linkedin/callback"
                          value={integrationForm.linkedin_redirect_uri || integrations.linkedin.redirect_uri}
                          onChange={(e) => setIntegrationForm({ ...integrationForm, linkedin_redirect_uri: e.target.value })}
                          className="flex-1 bg-white border border-[#E5E0D8] rounded-lg px-3 py-2 text-xs font-mono text-[#2C352B]"
                        />
                        <div className="flex gap-1.5 shrink-0">
                          <button
                            type="button"
                            onClick={() => setIntegrationForm({ ...integrationForm, linkedin_redirect_uri: 'http://127.0.0.1:8000/auth/linkedin/callback' })}
                            className="px-2.5 py-1.5 bg-white border border-[#E5E0D8] hover:bg-[#EFECE6] text-[11px] font-semibold rounded-lg"
                          >
                            Set 127.0.0.1
                          </button>
                          <button
                            type="button"
                            onClick={() => setIntegrationForm({ ...integrationForm, linkedin_redirect_uri: 'http://localhost:8000/auth/linkedin/callback' })}
                            className="px-2.5 py-1.5 bg-white border border-[#E5E0D8] hover:bg-[#EFECE6] text-[11px] font-semibold rounded-lg"
                          >
                            Set localhost
                          </button>
                        </div>
                      </div>
                    </div>

                    <div className="grid sm:grid-cols-2 gap-3">
                      <div>
                        <label className="text-xs font-semibold text-[#2C352B] block mb-1">Custom Client ID</label>
                        <input
                          type="text"
                          placeholder={integrations.linkedin.client_id_masked || "Leave blank for shared app"}
                          value={integrationForm.linkedin_client_id}
                          onChange={(e) => setIntegrationForm({ ...integrationForm, linkedin_client_id: e.target.value })}
                          className="w-full bg-white border border-[#E5E0D8] rounded-lg px-3 py-2 text-xs text-[#2C352B] font-mono focus:outline-none focus:border-[#3F513D]"
                        />
                      </div>
                      <div>
                        <label className="text-xs font-semibold text-[#2C352B] block mb-1">Custom Client Secret</label>
                        <input
                          type="password"
                          placeholder="Leave blank for shared app"
                          value={integrationForm.linkedin_client_secret}
                          onChange={(e) => setIntegrationForm({ ...integrationForm, linkedin_client_secret: e.target.value })}
                          className="w-full bg-white border border-[#E5E0D8] rounded-lg px-3 py-2 text-xs text-[#2C352B] font-mono focus:outline-none focus:border-[#3F513D]"
                        />
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      <button
                        type="button"
                        onClick={() => handleSaveAndConnect('linkedin')}
                        className="px-3.5 py-1.5 bg-[#3F513D] hover:bg-[#2D3A2C] text-white text-xs font-semibold rounded-lg shadow-sm"
                      >
                        Save Custom Credentials & Connect
                      </button>
                      {integrations.linkedin.has_custom_credentials && (
                        <button
                          type="button"
                          onClick={() => handleResetToShared('linkedin')}
                          className="px-3 py-1.5 bg-white border border-[#E5E0D8] text-[#8C2A2A] hover:bg-[#FDF2F2] text-xs font-semibold rounded-lg"
                        >
                          ↺ Revert to Central Shared App
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Reddit Integration Panel */}
            <div className="bg-white border border-[#E5E0D8] rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#E5E0D8]">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#FF4500]"></span>
                  <h3 className="font-bold text-sm text-[#2C352B]">Reddit Integration</h3>
                  {integrations.reddit.shared_oauth ? (
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-[#E2EBDD] text-[#2E542B] border border-[#B2C9B0]">
                      Shared App Ready
                    </span>
                  ) : (
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-[#FEF6E7] text-[#8C6B2A] border border-[#E8D4A8]">
                      Custom App Active ({integrations.reddit.client_id_masked})
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {accounts.reddit.connected ? (
                    <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-[#E2EBDD] text-[#2E542B] border border-[#B2C9B0]">
                      Connected: {accounts.reddit.accountName}
                    </span>
                  ) : (
                    <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-[#E5E0D8] text-[#6B7569]">
                      Not Connected
                    </span>
                  )}
                </div>
              </div>

              {/* Custom Reddit App Notice */}
              {integrations.reddit.has_custom_credentials && (
                <div className="bg-[#FEF6E7] border border-[#E8D4A8] rounded-lg p-3 text-xs text-[#8C6B2A] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                  <div>
                    <span className="font-bold flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-[#8C6B2A] shrink-0" />
                      Custom Reddit App Active: {integrations.reddit.client_id_masked}
                    </span>
                    <p className="text-[11px] text-[#71541D] mt-0.5">
                      Ensure your Reddit developer app includes the matching redirect URI below, or revert to the shared app.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleResetToShared('reddit')}
                    className="px-3 py-1.5 bg-[#8C6B2A] hover:bg-[#73531b] text-white rounded-lg text-xs font-semibold whitespace-nowrap shadow-sm"
                  >
                    ↺ Revert to Shared App
                  </button>
                </div>
              )}

              {/* Shared OAuth Status Banner */}
              <div className="bg-[#F4F7F4] border border-[#D3E1D2] rounded-lg p-4 space-y-2 text-xs text-[#334631]">
                <div className="font-bold text-[#233821] flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-[#2E542B]" />
                  {integrations.reddit.shared_oauth ? "Centralized Shared OAuth Ready:" : "Direct Authorization Available:"}
                </div>
                <p className="text-[11px] leading-relaxed">
                  {integrations.reddit.shared_oauth
                    ? "Reddit developer credentials are centrally configured on the secure backend. Authorize your personal Reddit account with a single click."
                    : "You are currently running with custom developer credentials. Click Connect below or expand Advanced to manage redirect URIs."}
                </p>
                <div className="flex items-center gap-3 pt-1">
                  {accounts.reddit.connected ? (
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleConnect('reddit')}
                        className="px-3.5 py-1.5 bg-[#FF4500] hover:bg-[#e03d00] text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-sm"
                      >
                        <RefreshCw className="w-3.5 h-3.5" /> Reconnect / Switch Profile
                      </button>
                      <button
                        onClick={() => handleDisconnect('reddit')}
                        className="px-3 py-1.5 bg-white border border-[#E5E0D8] text-[#8C2A2A] hover:bg-[#FDF2F2] rounded-lg text-xs font-semibold"
                      >
                        Disconnect
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => handleConnect('reddit')}
                      className="px-4 py-2 bg-[#FF4500] hover:bg-[#e03d00] text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-sm"
                    >
                      <ExternalLink className="w-3.5 h-3.5" /> Connect Reddit Account
                    </button>
                  )}
                  <span className="text-[11px] text-[#6B7569]">Scopes: <code>identity submit</code> (Permanent Token)</span>
                </div>
              </div>

              {/* Advanced Custom Credentials Accordion */}
              <div className="pt-1">
                <button
                  type="button"
                  onClick={() => setShowCustomRd(!showCustomRd)}
                  className="text-xs text-[#556153] hover:text-[#2C352B] font-semibold flex items-center gap-1"
                >
                  <span>{showCustomRd ? '▼ Hide' : '▶ Show'} Custom Developer Credentials (Advanced & Redirect URI Settings)</span>
                </button>

                {showCustomRd && (
                  <div className="mt-3 p-4 bg-[#FAF8F5] border border-[#E5E0D8] rounded-lg space-y-4">
                    <div className="p-3 bg-white border border-[#E5E0D8] rounded-lg space-y-2">
                      <div className="font-bold text-xs text-[#2C352B] flex items-center gap-1.5">
                        <Info className="w-4 h-4 text-[#FF4500]" /> Reddit Developer App Redirect URI Requirement:
                      </div>
                      <p className="text-[11px] text-[#6B7569] leading-relaxed">
                        In your Reddit App preferences (<a href="https://www.reddit.com/prefs/apps" target="_blank" rel="noreferrer" className="text-[#FF4500] underline font-semibold">reddit.com/prefs/apps</a>), enter the matching redirect URI:
                      </p>
                      <div className="space-y-1.5 pt-1">
                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            readOnly
                            value="http://127.0.0.1:8000/auth/reddit/callback"
                            className="flex-1 bg-[#F3EFEA] border border-[#E5E0D8] rounded px-2.5 py-1 text-[11px] font-mono text-[#2C352B] select-all"
                          />
                          <button
                            type="button"
                            onClick={() => copyToClipboard('http://127.0.0.1:8000/auth/reddit/callback')}
                            className="px-2.5 py-1 bg-white border border-[#E5E0D8] hover:bg-[#EFECE6] rounded text-[11px] font-semibold flex items-center gap-1"
                          >
                            <Copy className="w-3 h-3" /> Copy 127.0.0.1
                          </button>
                        </div>
                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            readOnly
                            value="http://localhost:8000/auth/reddit/callback"
                            className="flex-1 bg-[#F3EFEA] border border-[#E5E0D8] rounded px-2.5 py-1 text-[11px] font-mono text-[#2C352B] select-all"
                          />
                          <button
                            type="button"
                            onClick={() => copyToClipboard('http://localhost:8000/auth/reddit/callback')}
                            className="px-2.5 py-1 bg-white border border-[#E5E0D8] hover:bg-[#EFECE6] rounded text-[11px] font-semibold flex items-center gap-1"
                          >
                            <Copy className="w-3 h-3" /> Copy localhost
                          </button>
                        </div>
                      </div>
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-[#2C352B] block mb-1">Active Redirect URI used by AutoSocial Poster:</label>
                      <div className="flex flex-col sm:flex-row gap-2">
                        <input
                          type="text"
                          placeholder="http://127.0.0.1:8000/auth/reddit/callback"
                          value={integrationForm.reddit_redirect_uri || integrations.reddit.redirect_uri}
                          onChange={(e) => setIntegrationForm({ ...integrationForm, reddit_redirect_uri: e.target.value })}
                          className="flex-1 bg-white border border-[#E5E0D8] rounded-lg px-3 py-2 text-xs font-mono text-[#2C352B]"
                        />
                        <div className="flex gap-1.5 shrink-0">
                          <button
                            type="button"
                            onClick={() => setIntegrationForm({ ...integrationForm, reddit_redirect_uri: 'http://127.0.0.1:8000/auth/reddit/callback' })}
                            className="px-2.5 py-1.5 bg-white border border-[#E5E0D8] hover:bg-[#EFECE6] text-[11px] font-semibold rounded-lg"
                          >
                            Set 127.0.0.1
                          </button>
                          <button
                            type="button"
                            onClick={() => setIntegrationForm({ ...integrationForm, reddit_redirect_uri: 'http://localhost:8000/auth/reddit/callback' })}
                            className="px-2.5 py-1.5 bg-white border border-[#E5E0D8] hover:bg-[#EFECE6] text-[11px] font-semibold rounded-lg"
                          >
                            Set localhost
                          </button>
                        </div>
                      </div>
                    </div>

                    <div className="grid sm:grid-cols-3 gap-3">
                      <div>
                        <label className="text-xs font-semibold text-[#2C352B] block mb-1">Custom Client ID</label>
                        <input
                          type="text"
                          placeholder={integrations.reddit.client_id_masked || "Leave blank for shared app"}
                          value={integrationForm.reddit_client_id}
                          onChange={(e) => setIntegrationForm({ ...integrationForm, reddit_client_id: e.target.value })}
                          className="w-full bg-white border border-[#E5E0D8] rounded-lg px-3 py-2 text-xs text-[#2C352B] font-mono focus:outline-none focus:border-[#3F513D]"
                        />
                      </div>
                      <div>
                        <label className="text-xs font-semibold text-[#2C352B] block mb-1">Custom Client Secret</label>
                        <input
                          type="password"
                          placeholder="Leave blank for shared app"
                          value={integrationForm.reddit_client_secret}
                          onChange={(e) => setIntegrationForm({ ...integrationForm, reddit_client_secret: e.target.value })}
                          className="w-full bg-white border border-[#E5E0D8] rounded-lg px-3 py-2 text-xs text-[#2C352B] font-mono focus:outline-none focus:border-[#3F513D]"
                        />
                      </div>
                      <div>
                        <label className="text-xs font-semibold text-[#2C352B] block mb-1">Custom User-Agent</label>
                        <input
                          type="text"
                          value={integrationForm.reddit_user_agent}
                          onChange={(e) => setIntegrationForm({ ...integrationForm, reddit_user_agent: e.target.value })}
                          className="w-full bg-white border border-[#E5E0D8] rounded-lg px-3 py-2 text-xs text-[#2C352B] font-mono focus:outline-none focus:border-[#3F513D]"
                        />
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      <button
                        type="button"
                        onClick={() => handleSaveAndConnect('reddit')}
                        className="px-3.5 py-1.5 bg-[#3F513D] hover:bg-[#2D3A2C] text-white text-xs font-semibold rounded-lg shadow-sm"
                      >
                        Save Custom Credentials & Connect
                      </button>
                      {integrations.reddit.has_custom_credentials && (
                        <button
                          type="button"
                          onClick={() => handleResetToShared('reddit')}
                          className="px-3 py-1.5 bg-white border border-[#E5E0D8] text-[#8C2A2A] hover:bg-[#FDF2F2] text-xs font-semibold rounded-lg"
                        >
                          ↺ Revert to Central Shared App
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* License & Activation Panel */}
            <div className="bg-white border border-[#E5E0D8] rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#E5E0D8]">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-[#3F513D]" />
                  <h3 className="font-bold text-sm text-[#2C352B]">Client License & Activation</h3>
                </div>
                <span className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${
                  licenseStatus.activated ? 'bg-[#E2EBDD] text-[#2E542B] border-[#B2C9B0]' : 'bg-[#FEF6E7] text-[#8C6B2A] border-[#E8D4A8]'
                }`}>
                  {licenseStatus.activated ? `Activated (${licenseStatus.license_key})` : 'First-Run Key Required'}
                </span>
              </div>
              <p className="text-xs text-[#556153] leading-relaxed">
                Enter your issued license key to authorize this workstation installation.
              </p>
              <div className="max-w-xl flex gap-2">
                <input
                  type="text"
                  placeholder="e.g. ASPC-XXXX-XXXX-XXXX-XXXX"
                  value={licenseKeyInput}
                  onChange={(e) => setLicenseKeyInput(e.target.value.toUpperCase())}
                  className="flex-1 bg-[#FAF8F5] border border-[#E5E0D8] rounded-lg px-3 py-2 text-xs text-[#2C352B] font-mono focus:outline-none focus:border-[#3F513D]"
                />
                <button
                  onClick={handleActivateLicense}
                  className="px-4 py-2 bg-[#3F513D] hover:bg-[#2D3A2C] text-white text-xs font-semibold rounded-lg shadow-sm"
                >
                  Activate License
                </button>
              </div>
            </div>

            {/* Security Architecture Summary */}
            <div className="bg-[#FAF8F5] border border-[#E5E0D8] rounded-xl p-5 space-y-2 text-xs text-[#556153]">
              <div className="font-bold text-[#2C352B] flex items-center gap-1.5">
                <Lock className="w-4 h-4 text-[#3F513D]" /> Security & Anti-Spam Guardrails Summary:
              </div>
              <ul className="list-disc pl-5 space-y-1 text-[11px] leading-relaxed">
                <li><strong>Local Loopback Binding:</strong> Server strictly binds to <code>127.0.0.1</code> and never listens on external interfaces.</li>
                <li><strong>DPAPI Vault Encryption:</strong> Client secrets, Groq keys, and OAuth access/refresh tokens are stored encrypted in the Windows Credential Manager.</li>
                <li><strong>Dynamic Per-Launch Session Token:</strong> All internal API requests require a freshly generated cryptographic token.</li>
                <li><strong>Platform Rate Limits:</strong> Enforces a 5-post daily quota per platform with exponential backoff on HTTP 429 to protect accounts.</li>
                <li><strong>Duplicate Protection:</strong> Prevents identical content from re-publishing within 7 days.</li>
                <li><strong>Publishing Status Lock:</strong> Idempotent publishing state machine guarantees a post can never publish twice if interrupted.</li>
              </ul>
            </div>
          </div>
        )}
      </main>

      {/* ========================================================================= */}
      {/* 1. APPLICATION-STYLE SCHEDULING WINDOW / MODAL                            */}
      {/* ========================================================================= */}
      {scheduleModal.isOpen && (
        <div className="fixed inset-0 z-50 bg-[#2C352B]/40 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white border border-[#E5E0D8] rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4 my-8">
            <div className="flex items-center justify-between pb-3 border-b border-[#E5E0D8]">
              <div>
                <h3 className="text-sm font-bold text-[#2C352B] flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-[#3F513D]" /> Schedule Post Publication
                </h3>
                <p className="text-[11px] text-[#6B7569]">Set automated dispatch time & destination within the 7-day limit.</p>
              </div>
              <button
                onClick={() => setScheduleModal({ ...scheduleModal, isOpen: false })}
                className="p-1 hover:bg-[#EFECE6] rounded-md text-[#556153]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
              {/* Platform & Destination Selection */}
              <div className="grid sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-[#2C352B] block mb-1">Target Platform</label>
                  <select
                    value={scheduleModal.platform}
                    onChange={(e) => {
                      const plat = e.target.value;
                      const defaultDest = plat === 'linkedin' ? 'Personal Profile (Feed)' : (genForm.subreddit || 'r/smallbusiness');
                      setScheduleModal({ ...scheduleModal, platform: plat, destination: defaultDest });
                    }}
                    className="w-full bg-[#FAF8F5] border border-[#E5E0D8] rounded-lg px-3 py-2 text-xs text-[#2C352B] font-medium"
                  >
                    <option value="linkedin">LinkedIn</option>
                    <option value="reddit">Reddit</option>
                    {!scheduleModal.post && <option value="both">Both LinkedIn & Reddit</option>}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold text-[#2C352B] block mb-1">
                    {scheduleModal.platform === 'linkedin' ? 'LinkedIn Destination' : 'Reddit Subreddit'}
                  </label>
                  <input
                    type="text"
                    value={scheduleModal.destination}
                    onChange={(e) => setScheduleModal({ ...scheduleModal, destination: e.target.value })}
                    placeholder={scheduleModal.platform === 'linkedin' ? 'e.g. Personal Profile (Feed)' : 'e.g. r/smallbusiness'}
                    className="w-full bg-[#FAF8F5] border border-[#E5E0D8] rounded-lg px-3 py-2 text-xs text-[#2C352B]"
                  />
                </div>
              </div>

              {/* Destination quick chips */}
              {scheduleModal.platform === 'reddit' && (
                <div className="flex items-center gap-1.5 flex-wrap text-[11px]">
                  <span className="text-[#6B7569]">Quick Subreddits:</span>
                  {['r/smallbusiness', 'r/entrepreneur', 'r/SaaS', 'r/webdev'].map((sr) => (
                    <button
                      key={sr}
                      type="button"
                      onClick={() => setScheduleModal({ ...scheduleModal, destination: sr })}
                      className={`px-2 py-0.5 rounded text-[10px] font-mono transition ${
                        scheduleModal.destination === sr ? 'bg-[#3F513D] text-white' : 'bg-[#FAF8F5] border border-[#E5E0D8] text-[#556153]'
                      }`}
                    >
                      {sr}
                    </button>
                  ))}
                </div>
              )}

              {/* Date Selection: 7-Day Calendar Interface */}
              <div>
                <label className="text-xs font-semibold text-[#2C352B] block mb-1">
                  Scheduled Date (Interactive Calendar • Max 7 Days)
                </label>
                <CalendarPicker
                  selectedDate={scheduleModal.date}
                  onSelectDate={(newDate) => setScheduleModal({ ...scheduleModal, date: newDate })}
                />
              </div>

              {/* Time Selection */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-[#2C352B]">Scheduled Time</label>
                  <span className="text-[11px] text-[#6B7569]">
                    Timezone: <strong>{userTimezone}</strong>
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="time"
                    value={scheduleModal.time}
                    onChange={(e) => setScheduleModal({ ...scheduleModal, time: e.target.value })}
                    className="bg-[#FAF8F5] border border-[#E5E0D8] rounded-lg px-3 py-2 text-xs text-[#2C352B] font-mono flex-1"
                  />
                  <div className="flex items-center gap-1">
                    {['09:00', '12:00', '15:30', '18:00'].map((t) => (
                      <button
                        key={t}
                        type="button"
                        onClick={() => setScheduleModal({ ...scheduleModal, time: t })}
                        className={`px-2 py-1.5 rounded text-[10px] font-mono transition ${
                          scheduleModal.time === t ? 'bg-[#3F513D] text-white' : 'bg-[#FAF8F5] border border-[#E5E0D8] text-[#556153]'
                        }`}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Confirmation Section with TWO MANDATORY CHECKBOXES */}
              <div className="bg-[#FEF9EE] border border-[#E8D4A8] p-4 rounded-xl space-y-3">
                <div className="flex items-center gap-2 text-[#8C6B2A] text-xs font-bold">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>Automated Publication Confirmation</span>
                </div>
                <p className="text-[11px] text-[#7A5B20] leading-relaxed">
                  Scheduling this post represents your explicit approval. The post will be automatically dispatched at the selected date and time without any additional manual approval steps.
                </p>

                <div className="space-y-2 pt-1 border-t border-[#E8D4A8]/60">
                  <label className="flex items-start gap-2.5 cursor-pointer text-xs text-[#2C352B]">
                    <input
                      type="checkbox"
                      checked={scheduleModal.confirmDateTime}
                      onChange={(e) => setScheduleModal({ ...scheduleModal, confirmDateTime: e.target.checked })}
                      className="mt-0.5 rounded text-[#3F513D] focus:ring-[#3F513D]"
                    />
                    <span className="font-medium">
                      I have selected and confirmed the correct date and time ({scheduleModal.date} at {scheduleModal.time} {userTimezone}).
                    </span>
                  </label>

                  <label className="flex items-start gap-2.5 cursor-pointer text-xs text-[#2C352B]">
                    <input
                      type="checkbox"
                      checked={scheduleModal.confirmAutoPublish}
                      onChange={(e) => setScheduleModal({ ...scheduleModal, confirmAutoPublish: e.target.checked })}
                      className="mt-0.5 rounded text-[#3F513D] focus:ring-[#3F513D]"
                    />
                    <span className="font-medium">
                      I understand that this post will be automatically published at the selected time without requiring further approval.
                    </span>
                  </label>
                </div>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-between pt-3 border-t border-[#E5E0D8]">
              <span className="text-[11px] text-[#6B7569]">
                {!scheduleModal.confirmDateTime || !scheduleModal.confirmAutoPublish
                  ? 'Check both confirmations to enable'
                  : 'Ready to schedule'}
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setScheduleModal({ ...scheduleModal, isOpen: false })}
                  className="px-3.5 py-2 bg-[#FAF8F5] border border-[#E5E0D8] text-xs font-semibold text-[#2C352B] rounded-lg hover:bg-[#EFECE6]"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleScheduleSubmit}
                  disabled={!scheduleModal.confirmDateTime || !scheduleModal.confirmAutoPublish || !scheduleModal.date}
                  className="px-4 py-2 bg-[#3F513D] hover:bg-[#2D3A2C] text-white text-xs font-semibold rounded-lg transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5 shadow-sm"
                >
                  <Calendar className="w-3.5 h-3.5" /> Schedule Post
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 2. EDIT SCHEDULED POST MODAL                                              */}
      {/* ========================================================================= */}
      {editModal.isOpen && (
        <div className="fixed inset-0 z-50 bg-[#2C352B]/40 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white border border-[#E5E0D8] rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4 my-8">
            <div className="flex items-center justify-between pb-3 border-b border-[#E5E0D8]">
              <div>
                <h3 className="text-sm font-bold text-[#2C352B] flex items-center gap-2">
                  <Edit3 className="w-4 h-4 text-[#3F513D]" /> Edit Scheduled Post
                </h3>
                <p className="text-[11px] text-[#6B7569]">Update content, destination, or scheduled time.</p>
              </div>
              <button
                onClick={() => setEditModal({ ...editModal, isOpen: false })}
                className="p-1 hover:bg-[#EFECE6] rounded-md text-[#556153]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
              <div>
                <label className="text-xs font-semibold text-[#2C352B] block mb-1">Topic</label>
                <input
                  type="text"
                  value={editModal.topic}
                  onChange={(e) => setEditModal({ ...editModal, topic: e.target.value })}
                  className="w-full bg-[#FAF8F5] border border-[#E5E0D8] rounded-lg px-3 py-2 text-xs text-[#2C352B]"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-[#2C352B] block mb-1">Destination Target</label>
                <input
                  type="text"
                  value={editModal.destination}
                  onChange={(e) => setEditModal({ ...editModal, destination: e.target.value })}
                  className="w-full bg-[#FAF8F5] border border-[#E5E0D8] rounded-lg px-3 py-2 text-xs text-[#2C352B]"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-[#2C352B] block mb-1">Post Content</label>
                <textarea
                  rows={8}
                  value={editModal.content}
                  onChange={(e) => setEditModal({ ...editModal, content: e.target.value })}
                  className="w-full bg-[#FAF8F5] border border-[#E5E0D8] rounded-lg p-3 text-xs text-[#2C352B] leading-relaxed resize-none font-sans"
                />
              </div>

              {/* 7-Day Calendar Picker for Editing Date */}
              <div>
                <label className="text-xs font-semibold text-[#2C352B] block mb-1">
                  Scheduled Date (Select within 7-Day Window)
                </label>
                <CalendarPicker
                  selectedDate={editModal.date}
                  onSelectDate={(newDate) => setEditModal({ ...editModal, date: newDate })}
                />
              </div>

              {/* Time Selector */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-[#2C352B]">Execution Time</label>
                  <span className="text-[11px] text-[#6B7569]">Timezone: <strong>{userTimezone}</strong></span>
                </div>
                <input
                  type="time"
                  value={editModal.time}
                  onChange={(e) => setEditModal({ ...editModal, time: e.target.value })}
                  className="w-full bg-[#FAF8F5] border border-[#E5E0D8] rounded-lg px-3 py-2 text-xs text-[#2C352B] font-mono"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#E5E0D8]">
              <button
                type="button"
                onClick={() => setEditModal({ ...editModal, isOpen: false })}
                className="px-3.5 py-2 bg-[#FAF8F5] border border-[#E5E0D8] text-xs font-semibold text-[#2C352B] rounded-lg hover:bg-[#EFECE6]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleEditSave}
                className="px-4 py-2 bg-[#3F513D] hover:bg-[#2D3A2C] text-white text-xs font-semibold rounded-lg transition"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 3. API LOGS DRAWER                                                        */}
      {/* ========================================================================= */}
      <div
        className={`fixed bottom-0 left-0 right-0 z-40 bg-[#FAF8F5] border-t border-[#E5E0D8] transition-all duration-300 ${
          isLogDrawerOpen ? 'h-60' : 'h-9'
        }`}
      >
        <button
          onClick={() => setIsLogDrawerOpen(!isLogDrawerOpen)}
          className="w-full h-9 px-4 flex items-center justify-between text-xs text-[#556153] border-b border-[#E5E0D8]"
        >
          <span className="font-mono text-[#3F513D] font-bold">API Execution Logs ({logs.length})</span>
          <span className="text-[11px] font-medium">{isLogDrawerOpen ? 'Collapse' : 'Expand Log Terminal'}</span>
        </button>

        <div className="p-4 h-48 overflow-y-auto space-y-1.5 font-mono text-[11px] text-[#2C352B]">
          {logs.length === 0 ? (
            <span className="text-[#6B7569] italic">No API events recorded yet. Trigger actions to inspect payload requests.</span>
          ) : (
            logs.map((log) => (
              <div key={log.id} className="flex gap-2 border-b border-[#E5E0D8]/60 py-1">
                <span className="text-[#6B7569]">{log.timestamp}</span>
                <span className="font-bold text-[#3F513D]">{log.method}</span>
                <span>{log.endpoint}</span>
                <span className="text-[#3F513D]">[{log.status}]</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
