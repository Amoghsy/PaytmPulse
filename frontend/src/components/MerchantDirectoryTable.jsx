import React, { useState } from 'react';
import { 
  Store, 
  Search, 
  MapPin, 
  Phone, 
  Globe, 
  ShoppingBag, 
  Pill, 
  Utensils, 
  Smartphone, 
  Shirt, 
  Check, 
  ArrowRight,
  TrendingUp,
  Activity
} from 'lucide-react';
import Button from './ui/Button';

/**
 * Paytm Pulse - Universal Merchant Directory & Data Table
 * Light Mode Paytm-styled merchant network explorer.
 */
export function MerchantDirectoryTable({
  merchants = [],
  selectedMerchantId,
  onSelectMerchant,
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('ALL');

  const categories = ['ALL', 'KIRANA', 'PHARMACY', 'RESTAURANT', 'ELECTRONICS', 'CLOTHING'];

  const filteredMerchants = merchants.filter(m => {
    const matchesSearch = 
      (m.shop_name && m.shop_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (m.name && m.name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (m.location && m.location.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (m.city && m.city.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (m.business_name && m.business_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (m.category && m.category.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesCategory = categoryFilter === 'ALL' || (m.category && m.category.toUpperCase() === categoryFilter);

    return matchesSearch && matchesCategory;
  });

  const getCategoryIcon = (cat) => {
    switch (String(cat).toUpperCase()) {
      case 'KIRANA': return <ShoppingBag size={15} color="var(--paytm-cyan)" />;
      case 'PHARMACY': return <Pill size={15} color="var(--danger-color)" />;
      case 'RESTAURANT': return <Utensils size={15} color="var(--warning-color)" />;
      case 'ELECTRONICS': return <Smartphone size={15} color="var(--paytm-navy)" />;
      case 'CLOTHING': return <Shirt size={15} color="#8b5cf6" />;
      default: return <Store size={15} color="var(--paytm-cyan)" />;
    }
  };

  const totalNetworkRevenue = merchants.reduce((acc, m) => acc + (Number(m.total_revenue || m.revenue) || 0), 0);
  const totalTransactions = merchants.reduce((acc, m) => acc + (Number(m.total_transactions || m.transactions) || 0), 0);

  const formatINR = (val) => {
    return '₹' + Math.round(val || 0).toLocaleString('en-IN');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Top Banner & Network Stats */}
      <div style={{
        background: '#fff',
        border: '1px solid var(--border-color)',
        borderRadius: '12px',
        padding: '20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '16px'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--success-color)' }}></span>
            <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--paytm-navy)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              PostgreSQL Live Directory
            </span>
          </div>
          <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)', margin: '4px 0' }}>
            Merchant Network & Store Directory
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>
            Live merchants, categories, preferred languages, and real-time revenue performance.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
          <div style={{ background: 'var(--page-bg)', padding: '10px 16px', borderRadius: '10px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600 }}>STORES</div>
            <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--paytm-cyan)' }}>{merchants.length} Active</div>
          </div>
          <div style={{ background: 'var(--page-bg)', padding: '10px 16px', borderRadius: '10px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600 }}>NETWORK GMV</div>
            <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--success-color)' }}>{formatINR(totalNetworkRevenue)}</div>
          </div>
          <div style={{ background: 'var(--page-bg)', padding: '10px 16px', borderRadius: '10px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600 }}>TRANSACTIONS</div>
            <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--paytm-navy)' }}>{totalTransactions.toLocaleString()}</div>
          </div>
        </div>
      </div>

      {/* Search & Category Filter Controls */}
      <div style={{
        background: '#fff',
        border: '1px solid var(--border-color)',
        borderRadius: '12px',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px'
      }}>
        <div style={{ position: 'relative', width: '100%', maxWidth: '400px' }}>
          <Search size={16} color="var(--text-secondary)" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
          <input
            type="text"
            placeholder="Search by store name, owner, city, or category..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              padding: '9px 12px 9px 36px',
              borderRadius: '10px',
              border: '1px solid var(--border-color)',
              background: 'var(--page-bg)',
              fontSize: '13px',
              color: 'var(--text-primary)',
              outline: 'none'
            }}
          />
        </div>

        <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '2px' }}>
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                borderRadius: '16px',
                border: '1px solid',
                borderColor: categoryFilter === cat ? 'var(--paytm-cyan)' : 'var(--border-color)',
                background: categoryFilter === cat ? 'var(--info-tint)' : 'var(--surface-color)',
                color: categoryFilter === cat ? 'var(--paytm-navy)' : 'var(--text-secondary)',
                fontSize: '12px',
                fontWeight: categoryFilter === cat ? 600 : 500,
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              {cat !== 'ALL' && getCategoryIcon(cat)}
              {cat === 'ALL' ? 'All Categories' : cat.charAt(0) + cat.slice(1).toLowerCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Main Merchant Data Table */}
      <div style={{ background: '#fff', border: '1px solid var(--border-color)', borderRadius: '12px', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
          <thead>
            <tr style={{ background: 'var(--page-bg)', borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
              <th style={{ padding: '12px 16px' }}>Store & Merchant</th>
              <th style={{ padding: '12px 16px' }}>Category</th>
              <th style={{ padding: '12px 16px' }}>Location</th>
              <th style={{ padding: '12px 16px' }}>Language</th>
              <th style={{ padding: '12px 16px' }}>Revenue</th>
              <th style={{ padding: '12px 16px', textAlign: 'right' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredMerchants.length === 0 ? (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '36px 20px', color: 'var(--text-secondary)' }}>
                  No merchants found matching your query.
                </td>
              </tr>
            ) : (
              filteredMerchants.map((m, idx) => {
                const isSelected = m.id === selectedMerchantId;
                const shopName = m.business_name || m.shop_name || m.name || 'Store';
                const rev = Number(m.total_revenue || m.revenue || 0);

                return (
                  <tr
                    key={m.id || idx}
                    onClick={() => onSelectMerchant && onSelectMerchant(m)}
                    style={{
                      borderBottom: '1px solid var(--border-color)',
                      background: isSelected ? 'var(--info-tint)' : 'var(--surface-color)',
                      cursor: 'pointer'
                    }}
                  >
                    <td style={{ padding: '14px 16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div style={{
                          width: '32px',
                          height: '32px',
                          borderRadius: '8px',
                          background: isSelected ? 'var(--paytm-navy)' : 'var(--page-bg)',
                          color: isSelected ? '#fff' : 'var(--paytm-navy)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontWeight: 700
                        }}>
                          {shopName[0].toUpperCase()}
                        </div>
                        <div>
                          <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{shopName}</div>
                          <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>ID: {m.id}</div>
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      <span style={{ background: 'var(--page-bg)', padding: '3px 8px', borderRadius: '6px', fontSize: '12px' }}>
                        {m.category || 'Retail'}
                      </span>
                    </td>
                    <td style={{ padding: '14px 16px', color: 'var(--text-secondary)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <MapPin size={12} /> {m.city || m.location || 'India'}
                      </div>
                    </td>
                    <td style={{ padding: '14px 16px', fontWeight: 600, color: 'var(--paytm-navy)' }}>
                      {(m.preferred_language || m.language || 'en').toUpperCase()}
                    </td>
                    <td style={{ padding: '14px 16px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {formatINR(rev)}
                    </td>
                    <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                      {isSelected ? (
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '3px 8px', borderRadius: '10px', background: 'var(--paytm-cyan)', color: '#fff', fontSize: '11px', fontWeight: 600 }}>
                          <Check size={12} /> Selected
                        </span>
                      ) : (
                        <Button variant="ghost" size="sm">Select</Button>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default MerchantDirectoryTable;
