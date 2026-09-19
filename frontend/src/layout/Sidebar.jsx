import React from 'react';
import {
  LayoutDashboard,
  Zap,
  Target,
  Sparkles,
  Landmark,
  TrendingUp,
  Store,
  MapPin,
  Globe,
  MessageCircle,
  ArrowLeftRight,
  Boxes,
  X
} from 'lucide-react';

export function Sidebar({
  activeTab,
  onTabChange,
  onSelectTab,
  pendingDecisionsCount = 0,
  currentMerchant,
  activeMerchant,
  isMobileOpen = false,
  isOpen = false,
  onCloseMobile,
  onClose
}) {
  const merchant = currentMerchant || activeMerchant;
  const mobileOpen = isOpen || isMobileOpen;
  const handleTabClick = onSelectTab || onTabChange;
  const handleClose = onClose || onCloseMobile;

  const navSections = [
    {
      label: 'OVERVIEW',
      items: [
        { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
        { id: 'operations', label: 'Store Operations', icon: Boxes },
        { id: 'events', label: 'Live Events', icon: Zap }
      ]
    },
    {
      label: 'GROW',
      items: [
        {
          id: 'decisions',
          label: 'Decisions',
          icon: Target,
          badge: pendingDecisionsCount > 0 ? pendingDecisionsCount : null,
          badgeColor: 'var(--danger-color)'
        },
        { id: 'advisor', label: 'AI Advisor', icon: Sparkles },
        { id: 'financial', label: 'Financial Products', icon: Landmark }
      ]
    },
    {
      label: 'INSIGHTS',
      items: [
        { id: 'outcomes', label: 'Outcomes & ROI', icon: TrendingUp },
        { id: 'merchants', label: 'Merchants', icon: Store }
      ]
    }
  ];

  const catStr = merchant?.category?.replace('MerchantCategory.', '') || 'Retail Store';
  const langStr = merchant?.preferred_language || merchant?.language || 'Hindi';
  const shopName = merchant?.business_name || merchant?.shop_name || 'Active Store';

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {mobileOpen && (
        <div
          onClick={handleClose}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(15, 27, 45, 0.4)',
            zIndex: 999,
            backdropFilter: 'blur(2px)'
          }}
        />
      )}

      <aside className={`app-sidebar ${mobileOpen ? 'mobile-open' : ''}`}>
        {/* Navigation Items */}
        <div style={{ padding: '16px 12px', overflowY: 'auto', flex: 1 }}>
          {navSections.map((section, idx) => (
            <div key={idx} style={{ marginBottom: '20px' }}>
              <div
                style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  color: 'var(--text-secondary)',
                  letterSpacing: '0.6px',
                  padding: '4px 12px 8px 12px'
                }}
              >
                {section.label}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                {section.items.map(item => {
                  const Icon = item.icon;
                  const isActive = activeTab === item.id || (item.id === 'advisor' && activeTab === 'chat');

                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => {
                        if (handleTabClick) handleTabClick(item.id);
                        if (handleClose) handleClose();
                      }}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        width: '100%',
                        padding: '9px 12px',
                        borderRadius: '8px',
                        border: 'none',
                        borderLeft: isActive ? '3px solid var(--paytm-cyan)' : '3px solid transparent',
                        backgroundColor: isActive ? 'var(--info-tint)' : 'transparent',
                        color: isActive ? 'var(--paytm-navy)' : 'var(--text-secondary)',
                        fontWeight: isActive ? 600 : 500,
                        fontSize: '13.5px',
                        cursor: 'pointer',
                        textAlign: 'left',
                        transition: 'all 0.15s ease'
                      }}
                      onMouseEnter={(e) => {
                        if (!isActive) e.currentTarget.style.backgroundColor = 'var(--page-bg)';
                      }}
                      onMouseLeave={(e) => {
                        if (!isActive) e.currentTarget.style.backgroundColor = 'transparent';
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <Icon size={18} color={isActive ? 'var(--paytm-navy)' : 'var(--text-secondary)'} />
                        <span className="sidebar-nav-label">{item.label}</span>
                      </div>

                      {item.badge !== null && item.badge !== undefined && (
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 700,
                            color: '#FFFFFF',
                            backgroundColor: item.badgeColor || 'var(--danger-color)',
                            padding: '1px 6px',
                            borderRadius: '10px',
                            minWidth: '18px',
                            textAlign: 'center'
                          }}
                        >
                          {item.badge}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Bottom: Active Store Profile Card */}
        <div
          style={{
            padding: '14px',
            margin: '12px',
            backgroundColor: 'var(--page-bg)',
            border: '1px solid var(--border-color)',
            borderRadius: '10px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '6px',
                backgroundColor: 'var(--paytm-navy)',
                color: '#FFFFFF',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '12px',
                fontWeight: 700,
                flexShrink: 0
              }}
            >
              {shopName.charAt(0).toUpperCase()}
            </div>
            <div style={{ minWidth: 0, flex: 1 }}>
              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--paytm-navy)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {shopName}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {catStr}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-secondary)' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Globe size={11} /> {langStr.toUpperCase()}
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--success-color)', fontWeight: 600 }}>
              <span className="live-indicator-dot" style={{ width: '6px', height: '6px' }} /> Online
            </span>
          </div>
        </div>
      </aside>
    </>
  );
}

export default Sidebar;
