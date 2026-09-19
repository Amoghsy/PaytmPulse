import React, { useState } from 'react';
import { Activity, RefreshCw, Menu, Search } from 'lucide-react';
import { MerchantSwitcher } from './MerchantSwitcher';
import { StatusPopover } from './StatusPopover';
import { DemoMenu } from './DemoMenu';
import { seedDemoData, ingestTransactionEvent } from '../services/api';

export function Header({
  merchants = [],
  currentMerchant,
  activeMerchant,
  selectedMerchantId,
  onSelectMerchant,
  systemHealth,
  lastUpdated,
  lastRefreshed,
  isRefreshing,
  onRefresh,
  onRefreshData,
  onShowToast,
  onToggleSidebar,
  onToggleMobileSidebar,
  searchQuery,
  onSearchChange
}) {
  const [isSeeding, setIsSeeding] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);

  const merchant = currentMerchant || activeMerchant;
  const activeId = selectedMerchantId || (typeof merchant === 'object' ? merchant?.id : merchant);

  const initials = merchant?.business_name
    ? merchant.business_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : merchant?.name
      ? merchant.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
      : 'PP';

  const handleRefresh = onRefreshData || onRefresh;
  const handleToggleMenu = onToggleSidebar || onToggleMobileSidebar;

  const handleSeed = async () => {
    setIsSeeding(true);
    try {
      const response = await seedDemoData(false);
      if (response.ok) {
        if (onShowToast) onShowToast({ type: 'success', message: 'Demo Indian merchants, inventory & transactions seeded!' });
        if (handleRefresh) handleRefresh();
      } else {
        const err = response.data?.error || response.data?.detail || 'Failed to seed demo data.';
        if (onShowToast) onShowToast({ type: 'error', message: err });
      }
    } catch (err) {
      if (onShowToast) onShowToast({ type: 'error', message: 'Network error seeding demo data.' });
    } finally {
      setIsSeeding(false);
    }
  };

  const handleSimulate = async () => {
    if (!activeId) {
      if (onShowToast) onShowToast({ type: 'warning', message: 'Please select a merchant first.' });
      return;
    }
    setIsSimulating(true);
    try {
      const randomAmount = Math.floor(Math.random() * 800) + 150;
      const response = await ingestTransactionEvent({
        merchant_id: activeId,
        amount: randomAmount,
        payment_mode: 'UPI_QR',
        customer_phone: '9876543210',
        items: [{ name: 'Amul Butter 500g', quantity: 1, price: randomAmount }]
      });

      if (response.ok) {
        if (onShowToast) onShowToast({ type: 'success', message: `Simulated UPI payment of ₹${randomAmount} received!` });
        if (handleRefresh) handleRefresh();
      } else {
        const err = response.data?.error || response.data?.detail || 'Failed to simulate transaction.';
        if (onShowToast) onShowToast({ type: 'error', message: err });
      }
    } catch (err) {
      if (onShowToast) onShowToast({ type: 'error', message: 'Network error simulating transaction.' });
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <header
      style={{
        height: 'var(--header-height, 64px)',
        backgroundColor: '#FFFFFF',
        borderBottom: '1px solid var(--border-color)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        position: 'sticky',
        top: 0,
        zIndex: 90,
        boxShadow: 'var(--shadow-xs)'
      }}
    >
      {/* Left: Mobile Toggle + Wordmark */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <button
          type="button"
          onClick={handleToggleMenu}
          aria-label="Toggle Navigation"
          className="mobile-hamburger-btn"
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--paytm-navy)',
            cursor: 'pointer',
            padding: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          <Menu size={20} />
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, var(--paytm-navy) 0%, var(--paytm-cyan) 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#FFFFFF'
            }}
          >
            <Activity size={18} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', lineHeight: 1.1 }}>
              <span style={{ fontSize: '18px', fontWeight: 800, color: 'var(--paytm-navy)', letterSpacing: '-0.5px' }}>
                Paytm
              </span>
              <span style={{ fontSize: '18px', fontWeight: 800, color: 'var(--paytm-cyan)', letterSpacing: '-0.5px' }}>
                Pulse
              </span>
            </div>
            <span style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>
              AI Business Partner
            </span>
          </div>
        </div>
      </div>

      {/* Center: Global Search Box (Desktop) */}
      <div className="header-search-container" style={{ flex: 1, maxWidth: '380px', margin: '0 24px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '7px 12px',
            backgroundColor: 'var(--page-bg)',
            border: '1px solid var(--border-color)',
            borderRadius: '10px',
            transition: 'border-color 0.15s ease'
          }}
        >
          <Search size={15} color="var(--text-secondary)" />
          <input
            type="text"
            placeholder="Search merchants, products, telemetry..."
            value={searchQuery || ''}
            onChange={(e) => onSearchChange && onSearchChange(e.target.value)}
            style={{
              border: 'none',
              background: 'transparent',
              width: '100%',
              fontSize: '13px',
              color: 'var(--text-primary)',
              outline: 'none'
            }}
          />
        </div>
      </div>

      {/* Right Controls: MerchantSwitcher -> Health -> Refresh -> Demo Tools -> Avatar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <MerchantSwitcher
          merchants={merchants}
          selectedMerchantId={activeId}
          onSelect={onSelectMerchant}
        />

        <StatusPopover
          systemHealth={systemHealth}
          lastUpdated={lastUpdated || lastRefreshed}
        />

        {/* Refresh Icon Button */}
        <button
          type="button"
          onClick={handleRefresh}
          disabled={isRefreshing}
          title="Refresh All Telemetry"
          style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            border: '1px solid var(--border-color)',
            backgroundColor: '#FFFFFF',
            color: 'var(--paytm-navy)',
            cursor: isRefreshing ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: 'var(--shadow-xs)',
            transition: 'all 0.15s ease'
          }}
        >
          <RefreshCw size={15} style={{ animation: isRefreshing ? 'spin 1s linear infinite' : 'none' }} />
        </button>

        <DemoMenu
          onSeedData={handleSeed}
          onSimulateTransaction={handleSimulate}
          isSeeding={isSeeding}
          isSimulating={isSimulating}
        />

        {/* Merchant Avatar */}
        <div
          title={`${merchant?.business_name || 'Store'}`}
          style={{
            width: '36px',
            height: '36px',
            borderRadius: '50%',
            backgroundColor: 'var(--paytm-navy)',
            color: '#FFFFFF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '13px',
            fontWeight: 700,
            cursor: 'pointer',
            flexShrink: 0
          }}
        >
          {initials}
        </div>
      </div>
    </header>
  );
}

export default Header;
