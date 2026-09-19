import React, { useState } from 'react';
import { 
  Landmark, 
  Sparkles, 
  CheckCircle, 
  ArrowRight, 
  ShieldCheck, 
  Percent, 
  Volume2, 
  CreditCard, 
  Coins, 
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import PageHeader from '../layout/PageHeader';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Skeleton from '../components/ui/Skeleton';
import EmptyState from '../components/ui/EmptyState';
import { analyzeMerchantFinancialSignals } from '../services/api';

export default function Financial({ 
  currentMerchant, 
  financialProducts = [], 
  financialRecommendations = [], 
  loading = false, 
  onRefreshData,
  onShowToast 
}) {
  const [analyzing, setAnalyzing] = useState(false);

  const handleAnalyzeSignals = async () => {
    if (!currentMerchant?.id || analyzing) return;
    setAnalyzing(true);
    try {
      const response = await analyzeMerchantFinancialSignals(currentMerchant.id);
      if (response.ok) {
        if (onShowToast) onShowToast({ type: 'success', message: 'Financial intelligence analysis completed successfully.' });
        if (onRefreshData) onRefreshData();
      } else {
        const err = response.data?.error || response.data?.detail || 'Failed to analyze financial signals.';
        if (onShowToast) onShowToast({ type: 'error', message: err });
      }
    } catch (err) {
      if (onShowToast) onShowToast({ type: 'error', message: 'Error triggering financial evaluation.' });
    } finally {
      setAnalyzing(false);
    }
  };

  const getProductIcon = (productCode) => {
    const code = (productCode || '').toLowerCase();
    if (code.includes('soundbox') || code.includes('audio')) return <Volume2 size={24} color="var(--paytm-cyan)" />;
    if (code.includes('loan') || code.includes('credit') || code.includes('working_cap')) return <Landmark size={24} color="var(--paytm-navy)" />;
    if (code.includes('settle') || code.includes('payout')) return <Coins size={24} color="var(--success-color)" />;
    return <CreditCard size={24} color="var(--paytm-cyan)" />;
  };

  return (
    <div className="page-container">
      <PageHeader
        title="Financial Products & Working Capital"
        description={`Tailored Paytm credit and merchant growth instruments evaluated for ${currentMerchant?.business_name || 'your store'}.`}
        tag="Contextual Fintech"
        action={
          <Button
            variant="primary"
            icon={<Sparkles size={16} />}
            onClick={handleAnalyzeSignals}
            loading={analyzing}
            disabled={analyzing || !currentMerchant}
          >
            Analyze Financial Needs
          </Button>
        }
      />

      {/* Recommended for Merchant Hero Section */}
      <div style={{ marginBottom: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <Sparkles size={18} color="var(--paytm-cyan)" />
          <h2 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
            Recommended for {currentMerchant?.business_name || 'Active Merchant'}
          </h2>
        </div>

        {loading ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
            <Skeleton height="180px" borderRadius="12px" />
            <Skeleton height="180px" borderRadius="12px" />
          </div>
        ) : financialRecommendations && financialRecommendations.length > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '20px' }}>
            {financialRecommendations.map((rec, idx) => {
              const confidencePct = Math.round((rec.confidence_score || rec.match_score || 0.88) * 100);
              return (
                <Card 
                  key={rec.id || idx}
                  style={{
                    border: '1.5px solid var(--paytm-cyan)',
                    background: 'linear-gradient(180deg, #FFFFFF 0%, var(--info-tint) 100%)',
                    boxShadow: 'var(--shadow-md)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between'
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
                      <div style={{
                        width: '44px',
                        height: '44px',
                        borderRadius: '10px',
                        background: '#fff',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        boxShadow: '0 2px 5px rgba(0,0,0,0.06)'
                      }}>
                        {getProductIcon(rec.product_code || rec.product_name)}
                      </div>
                      <span style={{
                        background: 'var(--paytm-cyan)',
                        color: '#fff',
                        fontSize: '12px',
                        fontWeight: 700,
                        padding: '4px 10px',
                        borderRadius: '12px'
                      }}>
                        {confidencePct}% Match
                      </span>
                    </div>

                    <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--paytm-navy)', marginBottom: '6px' }}>
                      {rec.product_name || rec.product_code || 'Paytm Working Capital'}
                    </h3>
                    
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.5', marginBottom: '14px' }}>
                      {rec.reason || rec.recommendation_reason || 'Identified based on consistent daily UPI turnover and growth velocity.'}
                    </p>
                  </div>

                  <div style={{
                    paddingTop: '14px',
                    borderTop: '1px solid rgba(0, 46, 110, 0.08)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}>
                    <span style={{ fontSize: '12px', color: 'var(--text-secondary)', fontWeight: 500 }}>
                      Pre-approved Limit: <strong style={{ color: 'var(--text-primary)' }}>{rec.estimated_limit || '₹1,50,000'}</strong>
                    </span>
                    <Button 
                      variant="primary" 
                      size="sm"
                      onClick={() => {
                        if (onShowToast) onShowToast({ type: 'success', message: `Application started for ${rec.product_name || 'Product'}` });
                      }}
                    >
                      Apply Now
                    </Button>
                  </div>
                </Card>
              );
            })}
          </div>
        ) : (
          <Card>
            <EmptyState
              icon={Sparkles}
              title="No contextual recommendations yet"
              description={`Click "Analyze Financial Needs" above to evaluate ${currentMerchant?.business_name || 'this store'}'s UPI flow for Soundbox, working capital loans, or instant settlements.`}
              action={
                <Button variant="primary" size="sm" onClick={handleAnalyzeSignals} loading={analyzing}>
                  Run Financial Evaluation
                </Button>
              }
            />
          </Card>
        )}
      </div>

      {/* Complete Product Catalog */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <Landmark size={18} color="var(--paytm-navy)" />
          <h2 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
            Paytm Merchant Growth Catalog
          </h2>
        </div>

        {loading ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '20px' }}>
            <Skeleton height="200px" borderRadius="12px" />
            <Skeleton height="200px" borderRadius="12px" />
            <Skeleton height="200px" borderRadius="12px" />
          </div>
        ) : financialProducts && financialProducts.length > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '20px' }}>
            {financialProducts.map((prod, idx) => (
              <Card key={prod.id || idx} style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '10px',
                    background: 'var(--page-bg)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: '14px'
                  }}>
                    {getProductIcon(prod.code || prod.name)}
                  </div>

                  <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
                    {prod.name || prod.product_name}
                  </h3>

                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.5', marginBottom: '14px' }}>
                    {prod.description || 'Instant paperless approval linked to Soundbox transaction flow.'}
                  </p>

                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '16px' }}>
                    <span style={{ fontSize: '11px', background: 'var(--page-bg)', color: 'var(--text-secondary)', padding: '3px 8px', borderRadius: '6px' }}>
                      {prod.category || 'Fintech'}
                    </span>
                    <span style={{ fontSize: '11px', background: 'var(--info-tint)', color: 'var(--paytm-navy)', padding: '3px 8px', borderRadius: '6px' }}>
                      Zero Paperwork
                    </span>
                  </div>
                </div>

                <div style={{ paddingTop: '12px', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    Starting @ <strong style={{ color: 'var(--text-primary)' }}>{prod.interest_rate || '1.2%/mo'}</strong>
                  </span>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    icon={<ArrowRight size={14} />}
                    onClick={() => {
                      if (onShowToast) onShowToast({ type: 'info', message: `Viewing details for ${prod.name}` });
                    }}
                  >
                    Details
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '20px' }}>
            {/* Fallback Static Paytm Standard Products if backend catalog empty */}
            <Card>
              <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--info-tint)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '14px' }}>
                <Volume2 size={22} color="var(--paytm-cyan)" />
              </div>
              <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>Paytm Soundbox 4G</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '14px', lineHeight: '1.5' }}>
                Instant multilingual audio payment confirmation with long battery life.
              </p>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '12px', borderTop: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Rental: <strong>₹125/mo</strong></span>
                <Button variant="ghost" size="sm">Explore</Button>
              </div>
            </Card>

            <Card>
              <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--info-tint)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '14px' }}>
                <Landmark size={22} color="var(--paytm-navy)" />
              </div>
              <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>Merchant Collateral-Free Loan</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '14px', lineHeight: '1.5' }}>
                Up to ₹10 Lakhs working capital disbursed directly based on daily QR settlements.
              </p>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '12px', borderTop: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Interest: <strong>1.15%/mo</strong></span>
                <Button variant="ghost" size="sm">Explore</Button>
              </div>
            </Card>

            <Card>
              <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--info-tint)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '14px' }}>
                <Coins size={22} color="var(--success-color)" />
              </div>
              <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>Same-Day Instant Settlement</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '14px', lineHeight: '1.5' }}>
                Receive payments instantly in your bank account every 2 hours without waiting for T+1.
              </p>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '12px', borderTop: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Fee: <strong>0.05%</strong></span>
                <Button variant="ghost" size="sm">Explore</Button>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
