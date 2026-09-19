import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Sun,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Lightbulb,
  CheckCircle2,
  RefreshCw,
  Send,
  MessageSquare,
  ArrowRight,
  ShieldCheck,
  Zap
} from 'lucide-react';
import { Card } from './ui/Card';
import { Button } from './ui/Button';
import { fetchLatestBrief, generateMerchantBrief, sendWhatsAppBrief } from '../services/api';

export function PulseBriefCard({
  merchant,
  onNavigate,
  onShowToast
}) {
  const [brief, setBrief] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isSendingWhatsApp, setIsSendingWhatsApp] = useState(false);

  const merchantId = merchant?.id;

  const loadBrief = async () => {
    if (!merchantId) return;
    setLoading(true);
    try {
      const res = await fetchLatestBrief(merchantId);
      if (res.ok && res.data) {
        setBrief(res.data);
      } else {
        // Attempt auto-generate if not available
        const genRes = await generateMerchantBrief(merchantId, merchant?.language, false);
        if (genRes.ok && genRes.data) {
          setBrief(genRes.data);
        }
      }
    } catch (e) {
      console.error('Failed to load brief:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBrief();
  }, [merchantId]);

  const handleRefreshBrief = async () => {
    if (!merchantId || isRefreshing) return;
    setIsRefreshing(true);
    try {
      const res = await generateMerchantBrief(merchantId, merchant?.language, true);
      if (res.ok && res.data) {
        setBrief(res.data);
        if (onShowToast) {
          onShowToast({
            type: 'success',
            message: `Fresh AI Daily Brief synthesized for ${merchant?.business_name || 'Store'}!`
          });
        }
      } else {
        if (onShowToast) {
          onShowToast({
            type: 'error',
            message: res.data?.detail || 'Failed to refresh AI brief.'
          });
        }
      }
    } catch (e) {
      if (onShowToast) {
        onShowToast({ type: 'error', message: e.message || 'Network error refreshing brief.' });
      }
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleSendWhatsApp = async () => {
    if (!merchantId || isSendingWhatsApp) return;
    setIsSendingWhatsApp(true);
    try {
      const res = await sendWhatsAppBrief(merchantId);
      if (res.ok && res.data) {
        if (onShowToast) {
          onShowToast({
            type: 'success',
            message: `Daily brief dispatched via WhatsApp to ${merchant?.phone || 'registered phone'}!`
          });
        }
      } else {
        if (onShowToast) {
          onShowToast({
            type: 'error',
            message: res.data?.detail || 'Failed to dispatch WhatsApp message.'
          });
        }
      }
    } catch (e) {
      if (onShowToast) {
        onShowToast({ type: 'error', message: e.message || 'WhatsApp network error.' });
      }
    } finally {
      setIsSendingWhatsApp(false);
    }
  };

  if (loading && !brief) {
    return (
      <Card noPadding>
        <div style={{ padding: '24px', display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--color-text-secondary)' }}>
          <RefreshCw size={18} className="spin-animation" style={{ animation: 'spin 1s linear infinite' }} />
          <span style={{ fontSize: '14px' }}>Loading Paytm Pulse Daily Brief...</span>
        </div>
      </Card>
    );
  }

  const content = brief?.content || {};
  const keyMetrics = content.key_metrics || [];
  const attentionItems = content.attention_items || [];
  const opportunities = content.opportunities || [];
  const recommendedActions = content.recommended_actions || [];
  const isGemini = brief?.generated_by === 'gemini';

  return (
    <div
      style={{
        background: '#FFFFFF',
        borderRadius: 'var(--radius-xl)',
        border: '1px solid var(--color-border)',
        boxShadow: 'var(--shadow-sm)',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column'
      }}
    >
      {/* 1. Header Banner */}
      <div
        style={{
          padding: '16px 22px',
          background: 'linear-gradient(90deg, #F0F9FF 0%, #F5F7FA 100%)',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              backgroundColor: '#002E6E',
              color: '#00B9F5',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 6px rgba(0, 46, 110, 0.2)'
            }}
          >
            <Sun size={20} color="#FFB800" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '15px', fontWeight: 700, color: '#002E6E' }}>
                Today's Pulse Business Brief
              </span>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  backgroundColor: isGemini ? '#E6F8FE' : '#F1F5F9',
                  color: isGemini ? '#0079A6' : '#475569',
                  padding: '2px 8px',
                  borderRadius: '12px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                <Sparkles size={11} color={isGemini ? '#00B9F5' : '#64748B'} />
                {isGemini ? 'Powered by Gemini' : 'Pulse Telemetry'}
              </span>
            </div>
            <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
              {brief?.brief_date ? `Date: ${brief.brief_date}` : 'Morning intelligence summary'} &bull; Language: {brief?.language || 'English'}
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Button
            variant="secondary"
            size="sm"
            icon={<MessageSquare size={13} color="#25D366" />}
            onClick={handleSendWhatsApp}
            loading={isSendingWhatsApp}
            style={{ fontSize: '12px' }}
          >
            Send WhatsApp
          </Button>

          <Button
            variant="ghost"
            size="sm"
            icon={<RefreshCw size={13} className={isRefreshing ? 'spin-animation' : ''} />}
            onClick={handleRefreshBrief}
            loading={isRefreshing}
            style={{ fontSize: '12px' }}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* 2. Main Content Body */}
      <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Headline & Summary */}
        <div>
          <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-paytm-navy)', margin: '0 0 6px 0' }}>
            {brief?.headline || 'Good morning! Here is what needs your attention today.'}
          </h3>
          <p style={{ fontSize: '13.5px', color: 'var(--color-text-secondary)', margin: 0, lineHeight: 1.5 }}>
            {brief?.summary || 'Store metrics are healthy. Telemetry models are monitoring live store velocity.'}
          </p>
        </div>

        {/* Key Metrics Chips */}
        {keyMetrics.length > 0 && (
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            {keyMetrics.map((m, idx) => (
              <div
                key={idx}
                style={{
                  flex: '1 1 180px',
                  backgroundColor: '#F8FAFC',
                  border: '1px solid var(--color-border)',
                  borderRadius: '10px',
                  padding: '10px 14px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between'
                }}
              >
                <div>
                  <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                    {m.label}
                  </span>
                  <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-paytm-navy)', marginTop: '2px' }}>
                    {m.value}
                  </div>
                </div>
                {m.change && (
                  <span
                    style={{
                      fontSize: '11.5px',
                      fontWeight: 600,
                      color: m.trend === 'UP' ? 'var(--color-success)' : m.trend === 'DOWN' ? '#E11D48' : 'var(--color-text-secondary)',
                      backgroundColor: m.trend === 'UP' ? '#ECFDF5' : m.trend === 'DOWN' ? '#FFF1F2' : '#F1F5F9',
                      padding: '3px 7px',
                      borderRadius: '6px',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '3px'
                    }}
                  >
                    {m.trend === 'UP' ? <TrendingUp size={12} /> : m.trend === 'DOWN' ? <TrendingDown size={12} /> : null}
                    {m.change}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Attention & Opportunities Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
          {/* Attention Items */}
          {attentionItems.length > 0 && (
            <div
              style={{
                backgroundColor: '#FFFBEB',
                border: '1px solid #FDE68A',
                borderRadius: '10px',
                padding: '12px 14px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '10px'
              }}
            >
              <AlertTriangle size={18} color="#D97706" style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <span style={{ fontSize: '12px', fontWeight: 700, color: '#92400E', textTransform: 'uppercase' }}>
                  Attention Required ({attentionItems.length})
                </span>
                {attentionItems.slice(0, 2).map((item, i) => (
                  <p key={i} style={{ fontSize: '12.5px', color: '#78350F', margin: '4px 0 0 0', lineHeight: 1.4 }}>
                    <strong>{item.title}:</strong> {item.description}
                  </p>
                ))}
              </div>
            </div>
          )}

          {/* Opportunities */}
          {opportunities.length > 0 && (
            <div
              style={{
                backgroundColor: '#EFF6FF',
                border: '1px solid #BFDBFE',
                borderRadius: '10px',
                padding: '12px 14px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '10px'
              }}
            >
              <Lightbulb size={18} color="#2563EB" style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <span style={{ fontSize: '12px', fontWeight: 700, color: '#1E40AF', textTransform: 'uppercase' }}>
                  Top Growth Opportunity
                </span>
                {opportunities.slice(0, 1).map((opp, i) => (
                  <p key={i} style={{ fontSize: '12.5px', color: '#1E3A8A', margin: '4px 0 0 0', lineHeight: 1.4 }}>
                    <strong>{opp.title}:</strong> {opp.description} {opp.expected_impact ? `(Est: +${opp.expected_impact})` : ''}
                  </p>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Recommended Actions CTA */}
        {recommendedActions.length > 0 && (
          <div
            style={{
              padding: '12px 16px',
              backgroundColor: '#F8FAFC',
              border: '1px dashed var(--color-paytm-cyan)',
              borderRadius: '10px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '10px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Zap size={16} color="var(--color-paytm-navy)" />
              <span style={{ fontSize: '13px', color: 'var(--color-text-primary)' }}>
                <strong>Recommended Action:</strong> {recommendedActions[0].title} — {recommendedActions[0].reason}
              </span>
            </div>

            <Button
              variant="primary"
              size="sm"
              icon={<ArrowRight size={13} />}
              onClick={() => onNavigate && onNavigate('decisions')}
              style={{ fontSize: '12px' }}
            >
              Review & Approve
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

export default PulseBriefCard;
