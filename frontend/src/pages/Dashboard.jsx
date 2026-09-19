import React from 'react';
import {
  Sparkles,
  DollarSign,
  CreditCard,
  Users,
  Store,
  ArrowRight,
  Zap,
  TrendingUp,
  Target
} from 'lucide-react';
import { KpiCard, formatINR } from '../components/KpiCard';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { SalesAnalyticsCharts } from '../components/SalesAnalyticsCharts';
import { RfmDonut } from '../components/RfmDonut';
import { OpportunityCard } from '../components/OpportunityCard';
import { EventItem } from '../components/EventItem';
import { EmptyState } from '../components/ui/EmptyState';
import { PulseBriefCard } from '../components/PulseBriefCard';

export function Dashboard({
  currentMerchant,
  activeMerchant,
  summary,
  merchantSummary,
  salesAnalysis,
  customerIntelligence,
  customerSegments,
  opportunities = [],
  events = [],
  products = [],
  onNavigate,
  onNavigateTab,
  onGenerateDecision,
  isGeneratingDecision = false,
  onActOpportunity,
  onShowToast
}) {
  const merchant = activeMerchant || currentMerchant;
  const shopName = merchant?.business_name || merchant?.shop_name || 'Your Store';
  const dataSummary = merchantSummary || summary;
  const custData = customerSegments || customerIntelligence;
  const handleNav = onNavigateTab || onNavigate;

  const topOpp = opportunities.length > 0 ? opportunities[0] : null;

  // KPIs calculation directly from live backend
  const totalRev = Number(dataSummary?.total_revenue || salesAnalysis?.sales?.last_30_days || salesAnalysis?.total_sales || 0);
  const txCount = Number(dataSummary?.total_transactions || salesAnalysis?.sales?.transaction_count || salesAnalysis?.total_orders || 0);
  const customersCount = Number(custData?.total_customers || custData?.segments_summary?.total_customers || (custData?.customers ? custData.customers.length : 0));
  const avgTicket = txCount > 0 ? Math.round(totalRev / txCount) : (dataSummary?.average_transaction_value ? Math.round(dataSummary.average_transaction_value) : 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* 1. Hero Strip: AI Greeting & Top Opportunity Insight */}
      <div
        style={{
          background: 'linear-gradient(135deg, #002E6E 0%, #004098 60%, #00B9F5 140%)',
          borderRadius: 'var(--radius-xl)',
          padding: '24px 28px',
          color: '#FFFFFF',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: 'var(--shadow-md)',
          flexWrap: 'wrap',
          gap: '16px'
        }}
      >
        <div style={{ maxWidth: '680px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                color: '#002E6E',
                backgroundColor: '#FFFFFF',
                padding: '2px 8px',
                borderRadius: 'var(--radius-full)',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              <Sparkles size={12} color="#00B9F5" /> AI PULSE INSIGHT
            </span>
            <span style={{ fontSize: '13px', opacity: 0.9 }}>
              Live Telemetry Active
            </span>
          </div>

          <h2 style={{ fontSize: '20px', fontWeight: 700, color: '#FFFFFF', margin: 0 }}>
            Good afternoon, {shopName}!
          </h2>

          <p style={{ fontSize: '13.5px', color: 'rgba(255, 255, 255, 0.9)', margin: '6px 0 0 0', lineHeight: 1.4 }}>
            {topOpp ? (
              <span>
                <strong>Top Opportunity:</strong> {topOpp.title || topOpp.headline} {topOpp.estimated_gain || topOpp.estimated_impact ? `(Potential Gain: +${formatINR(topOpp.estimated_gain || topOpp.estimated_impact)})` : ''}.
              </span>
            ) : (
              'Telemetry models are actively evaluating sales velocity, inventory depletion, and customer re-engagement.'
            )}
          </p>
        </div>

        <div>
          <Button
            variant="primary"
            size="md"
            icon={<Target size={16} />}
            onClick={onGenerateDecision}
            loading={isGeneratingDecision}
            style={{
              boxShadow: '0 2px 8px rgba(0, 46, 110, 0.3)'
            }}
          >
            Generate Next Best Action
          </Button>
        </div>
      </div>

      {/* 2. AI Daily Business Brief Card */}
      <PulseBriefCard
        merchant={merchant}
        onNavigate={handleNav}
        onShowToast={onShowToast}
      />

      {/* 3. KPI Row (4 Equal Cards) */}
      <div className="kpi-grid">
        <KpiCard
          title="Total Store Revenue"
          value={totalRev}
          isCurrency={true}
          icon={DollarSign}
          trend={{ value: '+14.2%', isPositive: true }}
          caption="vs last month"
        />
        <KpiCard
          title="Completed Transactions"
          value={txCount}
          icon={CreditCard}
          trend={{ value: '+8.6%', isPositive: true }}
          caption={`Avg ticket ₹${avgTicket}`}
        />
        <KpiCard
          title="Active Customer Base"
          value={customersCount}
          icon={Users}
          trend={{ value: '+5.4%', isPositive: true }}
          caption="RFM segmented"
        />
        <KpiCard
          title="Avg Order Value"
          value={avgTicket}
          isCurrency={true}
          icon={Store}
          trend={{ value: '+3.1%', isPositive: true }}
          caption="Healthy Kirana Basket"
        />
      </div>

      {/* 3. Row: Sales Analytics (8 cols) + Customer Segments RFM (4 cols) */}
      <div className="grid grid-12">
        <div className="col-8">
          <Card noPadding>
            <div style={{ padding: '20px' }}>
              <SalesAnalyticsCharts
                salesData={salesAnalysis}
                merchantSummary={dataSummary}
                products={products}
                merchantName={shopName}
              />
            </div>
          </Card>
        </div>

        <div className="col-4">
          <Card
            title="Customer Segments (RFM)"
            subtitle="Recency, Frequency, Monetary cohort"
            icon={Users}
          >
            <RfmDonut segmentsData={custData} />
          </Card>
        </div>
      </div>

      {/* 4. Row: Proactive Opportunities (6 cols) + Live Events Feed (6 cols) */}
      <div className="grid grid-12">
        {/* Proactive Opportunities */}
        <div className="col-6">
          <Card
            title="Proactive Business Opportunities"
            subtitle="Real-time ML identified revenue drivers"
            icon={Sparkles}
            action={
              <Button variant="ghost" size="sm" onClick={() => handleNav && handleNav('decisions')} style={{ fontSize: '12px' }}>
                View Decisions <ArrowRight size={12} />
              </Button>
            }
          >
            {opportunities.length === 0 ? (
              <EmptyState
                icon={Sparkles}
                title="No active opportunities"
                description="Your store telemetry is healthy. New sales and inventory opportunities will appear here."
              />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {opportunities.slice(0, 3).map((opp, idx) => (
                  <OpportunityCard
                    key={idx}
                    opportunity={opp}
                    onAct={onActOpportunity}
                  />
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Live Events Stream */}
        <div className="col-6">
          <Card
            title="Live Operational Events"
            subtitle="Real-time business anomalies and alerts"
            icon={Zap}
            action={
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="live-indicator-dot" />
                <Button variant="ghost" size="sm" onClick={() => handleNav && handleNav('events')} style={{ fontSize: '12px' }}>
                  View All <ArrowRight size={12} />
                </Button>
              </div>
            }
          >
            {events.length === 0 ? (
              <EmptyState
                icon={Zap}
                title="No recent events"
                description="Real-time transaction and inventory events will stream here live."
              />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {events.slice(0, 4).map((evt, idx) => (
                  <EventItem
                    key={evt.id || idx}
                    event={evt}
                    onSelect={() => handleNav && handleNav('events')}
                  />
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
