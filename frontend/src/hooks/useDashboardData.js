import { useState, useEffect, useCallback, useRef } from 'react';
import {
  checkBackendHealth,
  checkDatabaseHealth,
  checkRedisHealth,
  checkN8nHealth,
  fetchMerchants,
  fetchMerchantSummary,
  fetchProducts,
  fetchTransactions,
  fetchBusinessEvents,
  fetchSalesAnalysis,
  fetchCustomerIntelligence,
  fetchMerchantOpportunities,
  fetchPendingDecisions,
  fetchMerchantDecisions,
  fetchMerchantOutcomes,
  fetchMerchantOutcomeSummary,
  fetchFeedbackSummary,
  fetchFeedbackPerformance,
  fetchFinancialProducts,
  fetchFinancialRecommendations,
  fetchMerchantConversationMemory
} from '../services/api';

function extractArray(data) {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.items)) return data.items;
  if (Array.isArray(data.opportunities)) return data.opportunities;
  if (Array.isArray(data.events)) return data.events;
  if (Array.isArray(data.decisions)) return data.decisions;
  if (Array.isArray(data.outcomes)) return data.outcomes;
  if (Array.isArray(data.products)) return data.products;
  if (Array.isArray(data.transactions)) return data.transactions;
  if (Array.isArray(data.results)) return data.results;
  if (Array.isArray(data.data)) return data.data;
  return [];
}

export function useDashboardData(pollInterval = 8000) {
  const [merchants, setMerchants] = useState([]);
  const [currentMerchant, setCurrentMerchant] = useState(null);
  const [summary, setSummary] = useState(null);
  const [products, setProducts] = useState([]);
  const [transactions, setTransactions] = useState([]);
  
  // Operational Telemetry & Intelligence Data
  const [events, setEvents] = useState([]);
  const [salesAnalysis, setSalesAnalysis] = useState(null);
  const [customerIntelligence, setCustomerIntelligence] = useState(null);
  const [opportunities, setOpportunities] = useState([]);
  const [pendingDecisions, setPendingDecisions] = useState([]);
  const [merchantDecisions, setMerchantDecisions] = useState([]);
  const [outcomes, setOutcomes] = useState([]);
  const [outcomeSummary, setOutcomeSummary] = useState(null);
  const [feedbackSummary, setFeedbackSummary] = useState(null);
  const [feedbackPerformance, setFeedbackPerformance] = useState([]);
  const [financialProducts, setFinancialProducts] = useState([]);
  const [financialRecommendations, setFinancialRecommendations] = useState([]);
  const [conversationMemory, setConversationMemory] = useState([]);

  // System Health
  const [systemHealth, setSystemHealth] = useState({
    backend: false,
    database: false,
    redis: false,
    n8n: false,
    allLive: false,
    lastChecked: null
  });

  // Loading States
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(new Date());

  const isPollingRef = useRef(false);

  // 1. Fetch System Health
  const checkHealth = useCallback(async () => {
    try {
      const [backendRes, dbRes, redisRes, n8nRes] = await Promise.all([
        checkBackendHealth(),
        checkDatabaseHealth(),
        checkRedisHealth(),
        checkN8nHealth()
      ]);

      const backendOk = backendRes.ok && (backendRes.data?.status === 'healthy' || backendRes.data?.status === 'ok');
      const dbOk = dbRes.ok && (dbRes.data?.status === 'healthy' || dbRes.data?.database === 'connected');
      const redisOk = redisRes.ok && (redisRes.data?.status === 'healthy' || redisRes.data?.redis === 'connected');
      const n8nOk = n8nRes.ok && (n8nRes.data?.status === 'healthy' || n8nRes.data?.n8n === 'connected');

      setSystemHealth({
        backend: backendOk,
        database: dbOk,
        redis: redisOk,
        n8n: n8nOk,
        allLive: backendOk && dbOk && redisOk,
        lastChecked: new Date()
      });
    } catch (e) {
      console.warn('Health check error:', e);
    }
  }, []);

  // 2. Fetch Merchant List & Set Default
  const loadMerchants = useCallback(async () => {
    try {
      const res = await fetchMerchants(50, 0);
      if (res.ok) {
        const merchantList = extractArray(res.data);
        setMerchants(merchantList);
        if (!currentMerchant && merchantList.length > 0) {
          setCurrentMerchant(merchantList[0]);
        } else if (currentMerchant) {
          const matched = merchantList.find(m => m.id === currentMerchant.id) || merchantList[0];
          setCurrentMerchant(matched);
        }
        return merchantList;
      }
    } catch (e) {
      console.warn('Error loading merchants:', e);
    }
    return [];
  }, [currentMerchant]);

  // 3. Load Active Merchant Scoped Intelligence & Telemetry
  const loadMerchantData = useCallback(async (merchantId, isBackground = false) => {
    if (!merchantId) return;
    if (!isBackground) setIsRefreshing(true);

    try {
      const [
        summaryRes,
        productsRes,
        txRes,
        eventsRes,
        salesRes,
        custIntelRes,
        oppsRes,
        pendingDecRes,
        allDecRes,
        outcomesRes,
        outcomeSumRes,
        feedbackSumRes,
        feedbackPerfRes,
        finProdRes,
        finRecsRes,
        chatMemRes
      ] = await Promise.all([
        fetchMerchantSummary(merchantId),
        fetchProducts(50, 0, merchantId),
        fetchTransactions(50, 0, merchantId),
        fetchBusinessEvents(merchantId, 25),
        fetchSalesAnalysis(merchantId, 30),
        fetchCustomerIntelligence(merchantId),
        fetchMerchantOpportunities(merchantId),
        fetchPendingDecisions(merchantId),
        fetchMerchantDecisions(merchantId),
        fetchMerchantOutcomes(merchantId, 30),
        fetchMerchantOutcomeSummary(merchantId, 30),
        fetchFeedbackSummary(merchantId),
        fetchFeedbackPerformance(90),
        fetchFinancialProducts(),
        fetchFinancialRecommendations(merchantId),
        fetchMerchantConversationMemory(merchantId, 20)
      ]);

      if (summaryRes.ok && summaryRes.data) setSummary(summaryRes.data);
      if (productsRes.ok) setProducts(extractArray(productsRes.data));
      if (txRes.ok) setTransactions(extractArray(txRes.data));
      if (eventsRes.ok) setEvents(extractArray(eventsRes.data));
      if (salesRes.ok && salesRes.data) setSalesAnalysis(salesRes.data);
      if (custIntelRes.ok && custIntelRes.data) setCustomerIntelligence(custIntelRes.data);
      if (oppsRes.ok) setOpportunities(extractArray(oppsRes.data));
      if (pendingDecRes.ok) setPendingDecisions(extractArray(pendingDecRes.data));
      if (allDecRes.ok) setMerchantDecisions(extractArray(allDecRes.data));
      if (outcomesRes.ok) setOutcomes(extractArray(outcomesRes.data));
      if (outcomeSumRes.ok && outcomeSumRes.data) setOutcomeSummary(outcomeSumRes.data);
      if (feedbackSumRes.ok && feedbackSumRes.data) setFeedbackSummary(feedbackSumRes.data);
      if (feedbackPerfRes.ok) setFeedbackPerformance(extractArray(feedbackPerfRes.data));
      if (finProdRes.ok) setFinancialProducts(extractArray(finProdRes.data));
      if (finRecsRes.ok) setFinancialRecommendations(extractArray(finRecsRes.data));
      if (chatMemRes.ok) setConversationMemory(extractArray(chatMemRes.data));

      setLastRefreshed(new Date());
    } catch (e) {
      console.warn('Error loading merchant telemetry:', e);
    } finally {
      if (!isBackground) setIsRefreshing(false);
      setLoading(false);
    }
  }, []);

  // Full Refresh Trigger
  const refreshData = useCallback(async () => {
    setIsRefreshing(true);
    await checkHealth();
    await loadMerchants();
    if (currentMerchant?.id) {
      await loadMerchantData(currentMerchant.id, false);
    }
    setIsRefreshing(false);
  }, [checkHealth, loadMerchants, currentMerchant?.id, loadMerchantData]);

  // Initial Load
  useEffect(() => {
    let mounted = true;
    const init = async () => {
      await checkHealth();
      const loadedMerchants = await loadMerchants();
      const firstId = loadedMerchants.length > 0 ? loadedMerchants[0].id : null;
      if (firstId && mounted) {
        await loadMerchantData(firstId, false);
      } else {
        setLoading(false);
      }
    };
    init();
    return () => { mounted = false; };
  }, []);

  // When merchant selection changes manually
  useEffect(() => {
    if (currentMerchant?.id) {
      loadMerchantData(currentMerchant.id, false);
    }
  }, [currentMerchant?.id]);

  // 8-second Non-Flashing Background Polling
  useEffect(() => {
    if (!pollInterval || pollInterval <= 0) return;

    const interval = setInterval(async () => {
      if (isPollingRef.current || !currentMerchant?.id) return;
      isPollingRef.current = true;
      try {
        await checkHealth();
        await loadMerchantData(currentMerchant.id, true);
      } catch (err) {
        console.warn('Polling error:', err);
      } finally {
        isPollingRef.current = false;
      }
    }, pollInterval);

    return () => clearInterval(interval);
  }, [pollInterval, currentMerchant?.id, checkHealth, loadMerchantData]);

  return {
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
    outcomes,
    outcomeSummary,
    feedbackSummary,
    feedbackPerformance,
    financialProducts,
    financialRecommendations,
    conversationMemory,
    systemHealth,
    lastRefreshed,
    loading,
    isRefreshing,
    refreshData
  };
}
