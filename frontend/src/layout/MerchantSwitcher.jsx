import React, { useState, useRef, useEffect } from 'react';
import { Store, ChevronDown, Check, Search, MapPin } from 'lucide-react';

export function MerchantSwitcher({ merchants = [], selectedMerchantId, onSelect }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const ref = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (ref.current && !ref.current.contains(event.target)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const currentId = typeof selectedMerchantId === 'object' ? selectedMerchantId?.id : selectedMerchantId;
  const activeMerchant = merchants.find(m => m.id === currentId) || merchants[0];

  const filteredMerchants = merchants.filter(m => {
    if (!search.trim()) return true;
    const term = search.toLowerCase();
    return (
      (m.shop_name || '').toLowerCase().includes(term) ||
      (m.name || '').toLowerCase().includes(term) ||
      (m.business_name || '').toLowerCase().includes(term) ||
      (m.location || '').toLowerCase().includes(term) ||
      (m.category || '').toLowerCase().includes(term)
    );
  });

  return (
    <div className="merchant-switcher-container" style={{ position: 'relative' }} ref={ref}>
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '6px 12px',
          backgroundColor: '#FFFFFF',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md)',
          cursor: 'pointer',
          outline: 'none',
          boxShadow: 'var(--shadow-xs)',
          maxWidth: '220px',
          textAlign: 'left'
        }}
      >
        <div
          style={{
            width: '28px',
            height: '28px',
            borderRadius: '6px',
            backgroundColor: 'var(--color-paytm-cyan-tint)',
            color: 'var(--color-text-cyan)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0
          }}
        >
          <Store size={15} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-paytm-navy)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {activeMerchant?.shop_name || activeMerchant?.business_name || 'Select Store'}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: '3px' }}>
            <MapPin size={10} /> {activeMerchant?.location?.split(',')[0] || 'Store'}
          </div>
        </div>
        <ChevronDown size={14} color="var(--color-text-muted)" />
      </button>

      {/* Dropdown Menu */}
      {open && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 8px)',
            right: 0,
            width: '320px',
            maxHeight: '400px',
            backgroundColor: '#FFFFFF',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-lg)',
            boxShadow: 'var(--shadow-popover)',
            zIndex: 1000,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            animation: 'toast-in 150ms ease'
          }}
        >
          {/* Search Box */}
          <div style={{ padding: '12px', borderBottom: '1px solid var(--color-border)' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px 10px',
                backgroundColor: 'var(--color-bg-page)',
                border: '1px solid var(--color-border)',
                borderRadius: '6px'
              }}
            >
              <Search size={14} color="var(--color-text-muted)" />
              <input
                type="text"
                placeholder="Search merchant or city..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{
                  border: 'none',
                  background: 'transparent',
                  width: '100%',
                  fontSize: '12px',
                  color: 'var(--color-text-primary)',
                  outline: 'none'
                }}
                autoFocus
              />
            </div>
          </div>

          {/* List of Merchants */}
          <div style={{ overflowY: 'auto', maxHeight: '280px', padding: '6px' }}>
            {filteredMerchants.length === 0 ? (
              <div style={{ padding: '16px', textAlign: 'center', fontSize: '12px', color: 'var(--color-text-muted)' }}>
                No merchants match your search.
              </div>
            ) : (
              filteredMerchants.map(m => {
                const isSelected = m.id === currentId;
                const catStr = m.category?.replace('MerchantCategory.', '') || 'KIRANA';
                return (
                  <div
                    key={m.id}
                    onClick={() => {
                      if (onSelect) {
                        onSelect(m);
                      }
                      setOpen(false);
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '8px 10px',
                      borderRadius: '6px',
                      backgroundColor: isSelected ? 'var(--color-paytm-cyan-tint)' : 'transparent',
                      cursor: 'pointer',
                      transition: 'background-color var(--transition-fast)'
                    }}
                    onMouseEnter={(e) => {
                      if (!isSelected) e.currentTarget.style.backgroundColor = 'var(--color-bg-page)';
                    }}
                    onMouseLeave={(e) => {
                      if (!isSelected) e.currentTarget.style.backgroundColor = 'transparent';
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
                      <div
                        style={{
                          width: '32px',
                          height: '32px',
                          borderRadius: '6px',
                          backgroundColor: isSelected ? 'var(--color-paytm-cyan)' : 'var(--color-bg-page)',
                          color: isSelected ? '#FFFFFF' : 'var(--color-paytm-navy)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '12px',
                          fontWeight: 600,
                          flexShrink: 0
                        }}
                      >
                        {m.name ? m.name.charAt(0).toUpperCase() : 'M'}
                      </div>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-paytm-navy)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {m.shop_name || m.business_name}
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', display: 'flex', gap: '6px' }}>
                          <span>{catStr}</span>
                          <span>•</span>
                          <span>{m.location}</span>
                        </div>
                      </div>
                    </div>
                    {isSelected && (
                      <Check size={16} color="var(--color-paytm-cyan-dark)" style={{ flexShrink: 0 }} />
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
