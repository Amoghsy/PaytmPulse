import React, { useState, useMemo } from 'react';
import { 
  Store, 
  Search, 
  Check, 
  MapPin, 
  Globe, 
  ArrowUpDown, 
  ChevronLeft, 
  ChevronRight,
  TrendingUp,
  CreditCard
} from 'lucide-react';
import PageHeader from '../layout/PageHeader';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Skeleton from '../components/ui/Skeleton';
import EmptyState from '../components/ui/EmptyState';

export default function Merchants({ 
  merchants = [], 
  currentMerchant, 
  onSelectMerchant, 
  loading = false, 
  onRefreshData,
  onShowToast 
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [sortField, setSortField] = useState('name');
  const [sortAsc, setSortAsc] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  const categories = useMemo(() => {
    const cats = new Set(merchants.map(m => m.category).filter(Boolean));
    return ['ALL', ...Array.from(cats)];
  }, [merchants]);

  const filteredMerchants = useMemo(() => {
    return merchants.filter(m => {
      const sTerm = searchTerm.toLowerCase();
      const shopName = (m.shop_name || m.business_name || m.name || '').toLowerCase();
      const location = (m.city || m.location || '').toLowerCase();
      const category = (m.category || '').toLowerCase();
      const owner = (m.name || '').toLowerCase();

      const matchSearch = 
        !searchTerm.trim() ||
        shopName.includes(sTerm) ||
        location.includes(sTerm) ||
        category.includes(sTerm) ||
        owner.includes(sTerm);
      
      const matchCat = selectedCategory === 'ALL' || m.category === selectedCategory;
      return matchSearch && matchCat;
    }).sort((a, b) => {
      let valA = a[sortField] || '';
      let valB = b[sortField] || '';
      if (sortField === 'name') {
        valA = a.shop_name || a.business_name || a.name || '';
        valB = b.shop_name || b.business_name || b.name || '';
      }
      if (typeof valA === 'string') {
        return sortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
      }
      return sortAsc ? valA - valB : valB - valA;
    });
  }, [merchants, searchTerm, selectedCategory, sortField, sortAsc]);

  const totalPages = Math.ceil(filteredMerchants.length / pageSize) || 1;
  const paginatedMerchants = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredMerchants.slice(start, start + pageSize);
  }, [filteredMerchants, currentPage, pageSize]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  const formatINR = (amount) => {
    if (amount === undefined || amount === null) return '₹0';
    return '₹' + Math.round(Number(amount)).toLocaleString('en-IN');
  };

  return (
    <div className="page-container">
      <PageHeader
        title="Merchant Directory & Store Switcher"
        description="Search, inspect, and switch active merchant context across multi-store Soundbox deployments."
        tag={`${merchants.length} Registered Stores`}
      />

      {/* Filter and Search Controls */}
      <Card style={{ marginBottom: '20px', padding: '16px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
            {/* Search Box */}
            <div style={{
              position: 'relative',
              flex: '1 1 280px',
              maxWidth: '400px'
            }}>
              <Search size={16} color="var(--color-text-muted)" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
                placeholder="Search shop name, city, category..."
                style={{
                  width: '100%',
                  padding: '9px 12px 9px 36px',
                  borderRadius: '10px',
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-bg-page)',
                  fontSize: '13px',
                  color: 'var(--color-text-primary)',
                  outline: 'none'
                }}
              />
            </div>

            {/* Pagination Controls */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                Page {currentPage} of {totalPages}
              </span>
              <Button
                variant="ghost"
                size="sm"
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              >
                <ChevronLeft size={16} />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              >
                <ChevronRight size={16} />
              </Button>
            </div>
          </div>

          {/* Category Chips */}
          <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '4px' }}>
            {categories.map(cat => (
              <button
                key={cat}
                onClick={() => { setSelectedCategory(cat); setCurrentPage(1); }}
                style={{
                  padding: '5px 12px',
                  borderRadius: '16px',
                  border: '1px solid',
                  borderColor: selectedCategory === cat ? 'var(--color-paytm-cyan)' : 'var(--color-border)',
                  background: selectedCategory === cat ? 'var(--color-paytm-cyan-tint)' : 'var(--color-bg-surface)',
                  color: selectedCategory === cat ? 'var(--color-paytm-navy)' : 'var(--color-text-secondary)',
                  fontSize: '12px',
                  fontWeight: selectedCategory === cat ? 600 : 500,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.15s ease'
                }}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Merchant Table Card */}
      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <Skeleton height="50px" />
            <Skeleton height="50px" />
            <Skeleton height="50px" />
          </div>
        ) : paginatedMerchants.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ background: 'var(--color-bg-page)', borderBottom: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }}>
                  <th style={{ padding: '14px 18px', fontWeight: 600, cursor: 'pointer' }} onClick={() => handleSort('name')}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      Shop & Merchant <ArrowUpDown size={13} />
                    </div>
                  </th>
                  <th style={{ padding: '14px 18px', fontWeight: 600, cursor: 'pointer' }} onClick={() => handleSort('category')}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      Category <ArrowUpDown size={13} />
                    </div>
                  </th>
                  <th style={{ padding: '14px 18px', fontWeight: 600, cursor: 'pointer' }} onClick={() => handleSort('city')}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      City / Location <ArrowUpDown size={13} />
                    </div>
                  </th>
                  <th style={{ padding: '14px 18px', fontWeight: 600 }}>Language</th>
                  <th style={{ padding: '14px 18px', fontWeight: 600 }}>Estimated GMV</th>
                  <th style={{ padding: '14px 18px', fontWeight: 600, textAlign: 'right' }}>Active Status</th>
                </tr>
              </thead>
              <tbody>
                {paginatedMerchants.map(m => {
                  const isActive = currentMerchant?.id === m.id;
                  const shopName = m.shop_name || m.business_name || m.name || 'Store';
                  const owner = m.name || 'Merchant';
                  const loc = m.city || m.location || 'India';
                  const lang = m.language || m.preferred_language || 'Hindi';

                  return (
                    <tr
                      key={m.id}
                      onClick={() => {
                        onSelectMerchant(m);
                        if (onShowToast) onShowToast({ type: 'info', message: `Switched store to ${shopName}` });
                      }}
                      style={{
                        borderBottom: '1px solid var(--color-border)',
                        background: isActive ? 'var(--color-paytm-cyan-tint)' : 'var(--color-bg-surface)',
                        cursor: 'pointer',
                        transition: 'background 0.15s ease'
                      }}
                      onMouseEnter={(e) => {
                        if (!isActive) e.currentTarget.style.background = 'rgba(0, 185, 245, 0.04)';
                      }}
                      onMouseLeave={(e) => {
                        if (!isActive) e.currentTarget.style.background = 'var(--color-bg-surface)';
                      }}
                    >
                      <td style={{ padding: '14px 18px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <div style={{
                            width: '36px',
                            height: '36px',
                            borderRadius: '8px',
                            background: isActive ? 'var(--color-paytm-navy)' : 'var(--color-bg-page)',
                            color: isActive ? '#fff' : 'var(--color-paytm-navy)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontWeight: 700,
                            fontSize: '13px'
                          }}>
                            {shopName[0].toUpperCase()}
                          </div>
                          <div>
                            <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>
                              {shopName}
                            </div>
                            <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>
                              Owner: {owner}
                            </div>
                          </div>
                        </div>
                      </td>

                      <td style={{ padding: '14px 18px' }}>
                        <span style={{
                          background: 'var(--color-bg-page)',
                          padding: '3px 8px',
                          borderRadius: '6px',
                          fontSize: '12px',
                          fontWeight: 500,
                          color: 'var(--color-text-secondary)'
                        }}>
                          {m.category || 'Retail'}
                        </span>
                      </td>

                      <td style={{ padding: '14px 18px', color: 'var(--color-text-secondary)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                          <MapPin size={13} color="var(--color-text-muted)" />
                          {loc}
                        </div>
                      </td>

                      <td style={{ padding: '14px 18px' }}>
                        <span style={{
                          fontSize: '12px',
                          fontWeight: 600,
                          color: 'var(--color-paytm-navy)',
                          textTransform: 'uppercase'
                        }}>
                          {lang}
                        </span>
                      </td>

                      <td style={{ padding: '14px 18px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                        {formatINR(m.revenue || m.total_revenue || 142850)}
                      </td>

                      <td style={{ padding: '14px 18px', textAlign: 'right' }}>
                        {isActive ? (
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '4px 10px',
                            borderRadius: '12px',
                            background: 'var(--color-paytm-cyan)',
                            color: '#fff',
                            fontSize: '12px',
                            fontWeight: 600
                          }}>
                            <Check size={13} /> Active Store
                          </span>
                        ) : (
                          <Button variant="ghost" size="sm">
                            Switch
                          </Button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={Store}
            title="No merchants found"
            description="Try changing your search query or clear category filters."
          />
        )}
      </Card>
    </div>
  );
}
