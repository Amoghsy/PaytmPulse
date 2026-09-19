const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Helper to perform fetch requests with error handling
 */
async function fetchEndpoint(endpoint) {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`);
    const data = await response.json().catch(() => null);
    
    return {
      ok: response.ok,
      status: response.status,
      data: data
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      data: { status: 'unhealthy', error: error.message }
    };
  }
}

/** Health Checks */
export async function checkAppMetadata() {
  return fetchEndpoint('/');
}

export async function checkBackendHealth() {
  return fetchEndpoint('/health');
}

export async function checkDatabaseHealth() {
  return fetchEndpoint('/health/database');
}

export async function checkRedisHealth() {
  return fetchEndpoint('/health/redis');
}

export async function checkN8nHealth() {
  return fetchEndpoint('/health/n8n');
}

/** Phase 2 Data Services */
export async function fetchMerchants(limit = 20, offset = 0) {
  return fetchEndpoint(`/merchants?limit=${limit}&offset=${offset}`);
}

export async function fetchProducts(limit = 20, offset = 0, merchantId = null) {
  const query = merchantId ? `&merchant_id=${merchantId}` : '';
  return fetchEndpoint(`/products?limit=${limit}&offset=${offset}${query}`);
}

export async function fetchCustomers(limit = 1, offset = 0) {
  return fetchEndpoint(`/customers?limit=${limit}&offset=${offset}`);
}

export async function fetchTransactions(limit = 50, offset = 0, merchantId = null) {
  const query = merchantId ? `&merchant_id=${merchantId}` : '';
  return fetchEndpoint(`/transactions?limit=${limit}&offset=${offset}${query}`);
}

export async function fetchMerchantSummary(merchantId) {
  return fetchEndpoint(`/merchants/${merchantId}/summary`);
}

/** Phase 3 Event Pipeline Services */
export async function fetchBusinessEvents(merchantId = null, limit = 20) {
  const query = merchantId ? `?merchant_id=${merchantId}&limit=${limit}` : `?limit=${limit}`;
  return fetchEndpoint(`/events${query}`);
}

export async function ingestTransactionEvent(payload) {
  try {
    const response = await fetch(`${API_BASE_URL}/events/transaction`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    return { ok: false, status: 0, data: { error: error.message } };
  }
}

/** Phase 4 ML Business Intelligence Services */
export async function fetchSalesAnalysis(merchantId, days = 30) {
  return fetchEndpoint(`/intelligence/sales/${merchantId}?days=${days}`);
}

export async function fetchAnomalyDetection(merchantId, productId = null) {
  try {
    const response = await fetch(`${API_BASE_URL}/intelligence/anomaly-detection`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ merchant_id: merchantId, product_id: productId })
    });
    const data = await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    return { ok: false, status: 0, data: { error: error.message } };
  }
}

export async function fetchDemandForecast(merchantId, productId) {
  try {
    const response = await fetch(`${API_BASE_URL}/intelligence/demand-forecast`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ merchant_id: merchantId, product_id: productId })
    });
    const data = await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    return { ok: false, status: 0, data: { error: error.message } };
  }
}

export async function fetchStockoutPrediction(merchantId, productId = null) {
  try {
    const response = await fetch(`${API_BASE_URL}/intelligence/stockout-prediction`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ merchant_id: merchantId, product_id: productId })
    });
    const data = await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    return { ok: false, status: 0, data: { error: error.message } };
  }
}

export async function fetchCustomerIntelligence(merchantId) {
  return fetchEndpoint(`/intelligence/customers/${merchantId}`);
}

export async function fetchMerchantOpportunities(merchantId) {
  return fetchEndpoint(`/intelligence/opportunities/${merchantId}`);
}

/** Phase 5 Agent Services */
export async function analyzeMerchantEvent(eventId) {
  try {
    const response = await fetch(`${API_BASE_URL}/agent/analyze-event`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event_id: eventId })
    });
    const data = await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    return { ok: false, status: 0, data: { error: error.message } };
  }
}

export async function sendAgentChatMessage(merchantId, message, language = null) {
  try {
    const payload = { merchant_id: merchantId, message };
    if (language) {
      payload.language = language;
    }
    let response = await fetch(`${API_BASE_URL}/agent/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (response.status === 404) {
      response = await fetch(`${API_BASE_URL}/api/v1/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    }
    const data = await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    return { ok: false, status: 0, data: { error: error.message } };
  }
}

/** AI Daily Business Brief Services */
export async function fetchLatestBrief(merchantId) {
  return fetchEndpoint(`/briefs/${merchantId}/latest`);
}

export async function fetchBriefHistory(merchantId, limit = 10) {
  return fetchEndpoint(`/briefs/${merchantId}/history?limit=${limit}`);
}

export async function generateMerchantBrief(merchantId, language = null, forceRefresh = false) {
  try {
    const payload = { merchant_id: merchantId, force_refresh: forceRefresh };
    if (language) payload.language = language;

    let response = await fetch(`${API_BASE_URL}/briefs/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (response.status === 404) {
      response = await fetch(`${API_BASE_URL}/api/v1/briefs/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    }
    const data = await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    return { ok: false, status: 0, data: { error: error.message } };
  }
}

export async function sendWhatsAppBrief(merchantId) {
  try {
    let response = await fetch(`${API_BASE_URL}/briefs/${merchantId}/send-whatsapp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    if (response.status === 404) {
      response = await fetch(`${API_BASE_URL}/api/v1/briefs/${merchantId}/send-whatsapp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
    }
    const data = await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    return { ok: false, status: 0, data: { error: error.message } };
  }
}

/** Phase 6 Decision Engine Services */
export async function generateNextBestAction(merchantId, eventId = null) {
  try {
    const response = await fetch(`${API_BASE_URL}/decisions/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ merchant_id: merchantId, event_id: eventId })
    });
    const data = await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    return { ok: false, status: 0, data: { error: error.message } };
  }
}

export async function fetchPendingDecisions(merchantId) {
  return fetchEndpoint(`/decisions/${merchantId}/pending`);
}

export async function fetchMerchantDecisions(merchantId) {
  return fetchEndpoint(`/decisions/${merchantId}`);
}

export async function approveDecision(decisionId) {
  try {
    const response = await fetch(`${API_BASE_URL}/decisions/${decisionId}/approve`, {
      method: 'POST'
    });
    const data = await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    return { ok: false, status: 0, data: { error: error.message } };
  }
}

export async function rejectDecision(decisionId) {
  try {
    const response = await fetch(`${API_BASE_URL}/decisions/${decisionId}/reject`, {
      method: 'POST'
    });
    const data = await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    return { ok: false, status: 0, data: { error: error.message } };
  }
}

/** Phase 11 Redis & Agent Fast Memory Services */
export async function fetchMemoryHealth() {
  return fetchEndpoint('/memory/health');
}

export async function fetchMerchantContextMemory(merchantId) {
  return fetchEndpoint(`/memory/${merchantId}/context`);
}

export async function fetchMerchantTransactionsMemory(merchantId, limit = 10) {
  return fetchEndpoint(`/memory/${merchantId}/transactions?limit=${limit}`);
}

export async function fetchMerchantAlertsMemory(merchantId) {
  return fetchEndpoint(`/memory/${merchantId}/alerts`);
}

export async function fetchMerchantSessionMemory(merchantId) {
  return fetchEndpoint(`/memory/${merchantId}/session`);
}

export async function fetchMerchantConversationMemory(merchantId, limit = 10) {
  return fetchEndpoint(`/memory/${merchantId}/conversation?limit=${limit}`);
}

export async function clearMerchantConversationMemory(merchantId) {
  try {
    const response = await fetch(`${API_BASE_URL}/memory/${merchantId}/conversation`, {
      method: 'DELETE'
    });
    const data = await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    return { ok: false, status: 0, data: { error: error.message } };
  }
}

/** Phase 12 Closed-Loop Outcome Measurement Services */
export async function measureActionOutcome(actionId, allowImmediate = true) {
  try {
    const response = await fetch(`${API_BASE_URL}/outcomes/measure/${actionId}?allow_immediate=${allowImmediate}`, {
      method: 'POST'
    });
    const data = await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    return { ok: false, status: 0, data: { error: error.message } };
  }
}

export async function fetchOutcome(outcomeId) {
  return fetchEndpoint(`/outcomes/${outcomeId}`);
}

export async function fetchOutcomeForAction(actionId) {
  return fetchEndpoint(`/outcomes/action/${actionId}`);
}

export async function fetchMerchantOutcomes(merchantId, limit = 50) {
  return fetchEndpoint(`/outcomes/merchant/${merchantId}?limit=${limit}`);
}

export async function fetchMerchantOutcomeSummary(merchantId, periodDays = 30) {
  return fetchEndpoint(`/outcomes/merchant/${merchantId}/summary?period_days=${periodDays}`);
}

export async function fetchOutcomeTrace(actionId) {
  return fetchEndpoint(`/outcomes/trace/${actionId}`);
}

/** Phase 8 Execution Services */
export async function executeAction(actionId) {
  try {
    const response = await fetch(`${API_BASE_URL}/execution/${actionId}`, {
      method: 'POST'
    });
    const data = await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    return { ok: false, status: 0, data: { error: error.message } };
  }
}

export async function fetchExecutionHistory(merchantId) {
  return fetchEndpoint(`/execution/history/${merchantId}`);
}

/** Phase 10 Contextual Financial Product Services */
export async function fetchFinancialProducts() {
  return fetchEndpoint('/financial/products');
}

export async function fetchFinancialRecommendations(merchantId) {
  return fetchEndpoint(`/financial/recommendations/${merchantId}`);
}

export async function analyzeMerchantFinancialSignals(merchantId) {
  try {
    const response = await fetch(`${API_BASE_URL}/financial/analyze/${merchantId}?bypass_cooldown=true`, {
      method: 'POST'
    });
    const data = await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    return { ok: false, status: 0, data: { error: error.message } };
  }
}

/** Phase 13 Continuous Learning & Feedback Services */
export async function fetchFeedbackSummary(merchantId) {
  return fetchEndpoint(`/feedback/merchant/${merchantId}/summary`);
}

export async function fetchFeedbackPerformance(lookbackDays = 90) {
  return fetchEndpoint(`/feedback/action-types?lookback_days=${lookbackDays}`);
}

/** Phase 7 Communication & Multilingual WhatsApp Services */
export async function triggerProactiveRecommendationAlert(decisionId, bypassCooldown = true, recipientPhone = null) {
  try {
    let url = `${API_BASE_URL}/communication/test-recommendation/${decisionId}?bypass_cooldown=${bypassCooldown}`;
    if (recipientPhone) {
      url += `&recipient_phone=${encodeURIComponent(recipientPhone)}`;
    }
    const response = await fetch(url, {
      method: 'POST'
    });
    const data = await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    return { ok: false, status: 0, data: { error: error.message } };
  }
}

export async function triggerProactiveEventAlert(merchantId, eventType = 'DEMAND_SPIKE', severity = 'HIGH', detailsMessage = null, bypassCooldown = true) {
  try {
    const query = new URLSearchParams({
      event_type: eventType,
      severity: severity,
      bypass_cooldown: bypassCooldown
    });
    if (detailsMessage) query.append('details_message', detailsMessage);

    const response = await fetch(`${API_BASE_URL}/communication/test-event-alert/${merchantId}?${query.toString()}`, {
      method: 'POST'
    });
    const data = await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    return { ok: false, status: 0, data: { error: error.message } };
  }
}

export async function broadcastMultilingualAlert(eventType = 'DEMAND_SPIKE', severity = 'HIGH', customMessage = null) {
  try {
    const query = new URLSearchParams({
      event_type: eventType,
      severity: severity
    });
    if (customMessage) query.append('custom_message', customMessage);

    const response = await fetch(`${API_BASE_URL}/communication/broadcast-multilingual?${query.toString()}`, {
      method: 'POST'
    });
    const data = await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    return { ok: false, status: 0, data: { error: error.message } };
  }
}

export async function fetchMerchantMessageHistory(merchantId, limit = 20) {
  return fetchEndpoint(`/communication/history/${merchantId}?limit=${limit}`);
}

/** System / Presentation Demo Seeder */
export async function seedDemoData(clearExisting = false) {
  try {
    const response = await fetch(`${API_BASE_URL}/system/seed?clear_existing=${clearExisting}`, {
      method: 'POST'
    });
    const data = await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    return { ok: false, status: 0, data: { error: error.message } };
  }
}

export async function fetchSystemOverview() {
  return fetchEndpoint('/system/overview');
}

