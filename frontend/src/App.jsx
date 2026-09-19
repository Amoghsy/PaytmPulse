import React, { useState } from 'react';
import Header from './layout/Header';
import Sidebar from './layout/Sidebar';
import { ToastContainer } from './components/ui/Toast';
import { useDashboardData } from './hooks/useDashboardData';
import { useToast } from './hooks/useToast';
import {
  generateNextBestAction,
  approveDecision,
  rejectDecision,
  triggerProactiveRecommendationAlert
} from './services/api';
import './App.css';

// Pages
import Dashboard from './pages/Dashboard';
import StoreOperations from './pages/StoreOperations';
import LiveEvents from './pages/LiveEvents';
import Decisions from './pages/Decisions';
import Advisor from './pages/Advisor';
import Financial from './pages/Financial';
import Outcomes from './pages/Outcomes';
import Merchants from './pages/Merchants';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { toasts, showToast, removeToast } = useToast();

  const [isGeneratingDecision, setIsGeneratingDecision] = useState(false);
  const [approvingId, setApprovingId] = useState(null);
  const [rejectingId, setRejectingId] = useState(null);
  const [alertingId, setAlertingId] = useState(null);

  const {
    merchants,
    currentMerchant,
    setCurrentMerchant,
    summary,
    products,
    transactions,
    events,
    salesAnalysis,
    customerIntelligence,
    opportunities,
    pendingDecisions,
    merchantDecisions,
    financialProducts,
    financialRecommendations,
    outcomes,
    outcomeSummary,
    feedbackSummary,
    feedbackPerformance,
    conversationMemory,
    systemHealth,
    lastRefreshed,
    loading,
    isRefreshing,
    refreshData,
  } = useDashboardData();

  const handleSelectMerchant = (merchantOrId) => {
    if (!merchantOrId) return;
    let target = merchantOrId;
    if (typeof merchantOrId === 'string') {
      target = merchants.find(m => m.id === merchantOrId) || { id: merchantOrId };
    }
    setCurrentMerchant(target);
    const shopTitle = target.shop_name || target.business_name || target.name || target.id;
    showToast({ type: 'info', message: `Active store switched to ${shopTitle}` });
  };

  const pendingCount = (pendingDecisions || []).length;

  const handleGenerateDecision = async (eventId = null) => {
    if (!currentMerchant?.id) {
      showToast({ type: 'warning', message: 'Please select an active merchant first.' });
      return;
    }
    setIsGeneratingDecision(true);
    try {
      const res = await generateNextBestAction(currentMerchant.id, eventId);
      if (res.ok) {
        showToast({
          type: 'success',
          message: 'Generated new Next Best Action recommendations based on latest sales & inventory telemetry!'
        });
        await refreshData();
      } else {
        showToast({
          type: 'error',
          message: res.data?.detail || res.data?.error || 'Failed to generate recommendations.'
        });
      }
    } catch (e) {
      showToast({ type: 'error', message: e.message || 'Error executing ML decision model.' });
    } finally {
      setIsGeneratingDecision(false);
    }
  };

  const handleApproveDecision = async (decisionId) => {
    setApprovingId(decisionId);
    try {
      const res = await approveDecision(decisionId);
      if (res.ok) {
        showToast({
          type: 'success',
          message: 'Decision approved & scheduled for execution via Paytm Soundbox / App.'
        });
        await refreshData();
      } else {
        showToast({
          type: 'error',
          message: res.data?.detail || res.data?.error || 'Approval failed.'
        });
      }
    } catch (e) {
      showToast({ type: 'error', message: e.message || 'Approval network error.' });
    } finally {
      setApprovingId(null);
    }
  };

  const handleRejectDecision = async (decisionId) => {
    setRejectingId(decisionId);
    try {
      const res = await rejectDecision(decisionId);
      if (res.ok) {
        showToast({
          type: 'info',
          message: 'Decision declined. Feedback recorded for ML model reinforcement.'
        });
        await refreshData();
      } else {
        showToast({
          type: 'error',
          message: res.data?.detail || res.data?.error || 'Rejection failed.'
        });
      }
    } catch (e) {
      showToast({ type: 'error', message: e.message || 'Rejection network error.' });
    } finally {
      setRejectingId(null);
    }
  };

  const handleSendWhatsAppAlert = async (decisionId) => {
    setAlertingId(decisionId);
    try {
      const res = await triggerProactiveRecommendationAlert(decisionId, true);
      if (res.ok && res.data) {
        if (res.data.status === 'FAILED') {
          showToast({
            type: 'error',
            message: `WhatsApp Delivery Issue: ${res.data.message_text || 'Meta Cloud API rejected message.'}`,
            duration: 8000
          });
        } else {
          const lang = currentMerchant?.language || currentMerchant?.preferred_language || 'Hindi';
          showToast({
            type: 'success',
            message: res.data.message_text || `WhatsApp decision alert dispatched in ${lang} to ${currentMerchant?.phone || 'registered phone'}!`,
            duration: 6000
          });
        }
        await refreshData();
      } else {
        showToast({
          type: 'error',
          message: res.data?.detail || res.data?.error || 'Failed to trigger WhatsApp communication service.',
          duration: 6000
        });
      }
    } catch (e) {
      showToast({ type: 'error', message: e.message || 'WhatsApp dispatch network error.' });
    } finally {
      setAlertingId(null);
    }
  };

  const renderActivePage = () => {
    switch (activeTab) {
      case 'dashboard':
        return (
          <Dashboard
            currentMerchant={currentMerchant}
            summary={summary}
            salesAnalysis={salesAnalysis}
            customerIntelligence={customerIntelligence}
            opportunities={opportunities}
            events={events}
            products={products}
            loading={loading}
            onNavigate={(tab) => setActiveTab(tab)}
            onRefreshData={refreshData}
            onShowToast={showToast}
            onGenerateDecision={() => handleGenerateDecision()}
            isGeneratingDecision={isGeneratingDecision}
            onActOpportunity={() => handleGenerateDecision()}
          />
        );

      case 'operations':
        return (
          <StoreOperations
            currentMerchant={currentMerchant}
            transactions={transactions}
            products={products}
            loading={loading}
            onRefreshData={refreshData}
            onShowToast={showToast}
          />
        );

      case 'events':
        return (
          <LiveEvents
            currentMerchant={currentMerchant}
            events={events}
            loading={loading}
            onRefreshData={refreshData}
            onShowToast={showToast}
          />
        );

      case 'decisions':
        return (
          <Decisions
            activeMerchant={currentMerchant}
            pendingDecisions={pendingDecisions}
            decisionHistory={merchantDecisions}
            loading={loading}
            onRefresh={refreshData}
            onGenerateDecision={() => handleGenerateDecision()}
            isGenerating={isGeneratingDecision}
            onApproveDecision={handleApproveDecision}
            onRejectDecision={handleRejectDecision}
            onSendWhatsAppAlert={handleSendWhatsAppAlert}
            approvingId={approvingId}
            rejectingId={rejectingId}
            alertingId={alertingId}
            onShowToast={showToast}
          />
        );

      case 'advisor':
        return (
          <Advisor
            currentMerchant={currentMerchant}
            conversationMemory={conversationMemory}
            onRefreshData={refreshData}
            onShowToast={showToast}
          />
        );

      case 'financial':
        return (
          <Financial
            currentMerchant={currentMerchant}
            financialProducts={financialProducts}
            financialRecommendations={financialRecommendations}
            loading={loading}
            onRefreshData={refreshData}
            onShowToast={showToast}
          />
        );

      case 'outcomes':
        return (
          <Outcomes
            currentMerchant={currentMerchant}
            outcomes={outcomes}
            outcomeSummary={outcomeSummary}
            feedbackSummary={feedbackSummary}
            feedbackPerformance={feedbackPerformance}
            loading={loading}
            onRefreshData={refreshData}
            onShowToast={showToast}
          />
        );

      case 'merchants':
        return (
          <Merchants
            merchants={merchants}
            currentMerchant={currentMerchant}
            onSelectMerchant={handleSelectMerchant}
            loading={loading}
            onRefreshData={refreshData}
            onShowToast={showToast}
          />
        );

      default:
        return (
          <Dashboard
            currentMerchant={currentMerchant}
            summary={summary}
            salesAnalysis={salesAnalysis}
            customerIntelligence={customerIntelligence}
            opportunities={opportunities}
            events={events}
            loading={loading}
            onNavigate={(tab) => setActiveTab(tab)}
            onRefreshData={refreshData}
            onShowToast={showToast}
          />
        );
    }
  };

  return (
    <div className="app-layout">
      {/* 64px Top Header */}
      <Header
        currentMerchant={currentMerchant}
        merchants={merchants}
        onSelectMerchant={handleSelectMerchant}
        systemHealth={systemHealth}
        lastRefreshed={lastRefreshed}
        isRefreshing={isRefreshing}
        onRefreshData={refreshData}
        onShowToast={showToast}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      />

      <div className="main-wrapper">
        {/* Left Sidebar Navigation */}
        <Sidebar
          activeTab={activeTab}
          onSelectTab={(tab) => {
            setActiveTab(tab);
            setSidebarOpen(false);
          }}
          pendingDecisionsCount={pendingCount}
          currentMerchant={currentMerchant}
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />

        {/* Main Content Area */}
        <main className="content-area">
          {renderActivePage()}
        </main>
      </div>

      {/* Toast Notification Container */}
      <ToastContainer toasts={toasts} onCloseToast={removeToast} />
    </div>
  );
}
