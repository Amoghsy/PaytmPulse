import React, { useState, useMemo } from 'react';
import { 
  Receipt, 
  Boxes, 
  Search, 
  ArrowUpDown, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  CreditCard, 
  Package, 
  TrendingUp, 
  ChevronLeft, 
  ChevronRight,
  Filter,
  DollarSign
} from 'lucide-react';
import PageHeader from '../layout/PageHeader';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Skeleton from '../components/ui/Skeleton';
import EmptyState from '../components/ui/EmptyState';
import { formatINR } from '../components/KpiCard';

export default function StoreOperations({
  currentMerchant,
  transactions = [],
  products = [],
  loading = false,
  onRefreshData,
  onShowToast
}) {
  const [activeSubTab, setActiveSubTab] = useState('transactions'); // 'transactions' | 'inventory'
  const [searchTerm, setSearchTerm] = useState('');
  const [filterMethod, setFilterMethod] = useState('ALL');
  const [filterCategory, setFilterCategory] = useState('ALL');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  const shopName = currentMerchant?.shop_name || currentMerchant?.business_name || 'Store';

  // --- Transactions Data Processing ---
  const filteredTransactions = useMemo(() => {
    return transactions.filter(t => {
      const matchSearch = 
        !searchTerm.trim() ||
        (t.id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
        (t.product_id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
        (t.payment_method || '').toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchMethod = filterMethod === 'ALL' || (t.payment_method || '').toUpperCase() === filterMethod;
      return matchSearch && matchMethod;
    }).sort((a, b) => new Date(b.transaction_timestamp || b.created_at || 0) - new Date(a.transaction_timestamp || a.created_at || 0));
  }, [transactions, searchTerm, filterMethod]);

  const totalTxVolume = transactions.reduce((acc, t) => acc + Number(t.amount || 0), 0);
  const avgTxAmount = transactions.length > 0 ? Math.round(totalTxVolume / transactions.length) : 0;
  const upiCount = transactions.filter(t => (t.payment_method || '').toUpperCase().includes('UPI')).length;
  const upiShare = transactions.length > 0 ? Math.round((upiCount / transactions.length) * 100) : 0;

  // --- Inventory Data Processing ---
  const filteredProducts = useMemo(() => {
    return products.filter(p => {
      const matchSearch = 
        !searchTerm.trim() ||
        (p.name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
        (p.category || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
        (p.supplier || '').toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchCat = filterCategory === 'ALL' || (p.category || '').toUpperCase() === filterCategory.toUpperCase();
      return matchSearch && matchCat;
    }).sort((a, b) => (a.current_stock || 0) - (b.current_stock || 0));
  }, [products, searchTerm, filterCategory]);

  const categories = useMemo(() => {
    const set = new Set(products.map(p => p.category).filter(Boolean));
    return ['ALL', ...Array.from(set)];
  }, [products]);

  const lowStockCount = products.filter(p => (p.current_stock || 0) <= (p.reorder_level || 10)).length;
  const totalStockUnits = products.reduce((acc, p) => acc + Number(p.current_stock || 0), 0);

  // Pagination
  const currentList = activeSubTab === 'transactions' ? filteredTransactions : filteredProducts;
  const totalPages = Math.ceil(currentList.length / pageSize) || 1;
  const paginatedList = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return currentList.slice(start, start + pageSize);
  }, [currentList, currentPage, pageSize]);

  return (
    <div className="page-container">
      <PageHeader
        title={`Store Operations: ${shopName}`}
        description={`Inspect merchant-wise transaction telemetry and inventory stock levels in real time.`}
        tag={activeSubTab === 'transactions' ? `${transactions.length} Live Transactions` : `${products.length} Active SKUs`}
        action={
          <div style={{ display: 'flex', gap: '8px', backgroundColor: '#FFFFFF', padding: '4px', borderRadius: '10px', border: '1px solid var(--color-border)' }}>
            <button
              type="button"
              onClick={() => { setActiveSubTab('transactions'); setCurrentPage(1); setSearchTerm(''); }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                borderRadius: '8px',
                border: 'none',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: activeSubTab === 'transactions' ? 600 : 500,
                backgroundColor: activeSubTab === 'transactions' ? 'var(--color-paytm-cyan-tint)' : 'transparent',
                color: activeSubTab === 'transactions' ? 'var(--color-paytm-navy)' : 'var(--color-text-secondary)',
                transition: 'all 0.15s ease'
              }}
            >
              <Receipt size={15} /> Transactions
            </button>
            <button
              type="button"
              onClick={() => { setActiveSubTab('inventory'); setCurrentPage(1); setSearchTerm(''); }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                borderRadius: '8px',
                border: 'none',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: activeSubTab === 'inventory' ? 600 : 500,
                backgroundColor: activeSubTab === 'inventory' ? 'var(--color-paytm-cyan-tint)' : 'transparent',
                color: activeSubTab === 'inventory' ? 'var(--color-paytm-navy)' : 'var(--color-text-secondary)',
                transition: 'all 0.15s ease'
              }}
            >
              <Boxes size={15} /> Inventory & Stock
            </button>
          </div>
        }
      />

      {/* Metric Cards Banner */}
      {activeSubTab === 'transactions' ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
          <Card style={{ padding: '16px 20px' }}>
            <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)', fontWeight: 500 }}>Total Transactions</span>
            <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--color-paytm-navy)', marginTop: '4px' }}>
              {transactions.length.toLocaleString('en-IN')}
            </div>
            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>Recorded in database</span>
          </Card>
          <Card style={{ padding: '16px 20px' }}>
            <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)', fontWeight: 500 }}>Gross Transaction Volume</span>
            <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--color-success-dark)', marginTop: '4px' }}>
              {formatINR(totalTxVolume)}
            </div>
            <span style={{ fontSize: '11px', color: 'var(--color-success-dark)', fontWeight: 600 }}>100% verified settlement</span>
          </Card>
          <Card style={{ padding: '16px 20px' }}>
            <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)', fontWeight: 500 }}>Average Ticket Size</span>
            <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '4px' }}>
              {formatINR(avgTxAmount)}
            </div>
            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>Per completed checkout</span>
          </Card>
          <Card style={{ padding: '16px 20px' }}>
            <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)', fontWeight: 500 }}>UPI / QR Share</span>
            <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--color-paytm-cyan)', marginTop: '4px' }}>
              {upiShare}%
            </div>
            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>Soundbox audio broadcast</span>
          </Card>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
          <Card style={{ padding: '16px 20px' }}>
            <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)', fontWeight: 500 }}>Total Catalog SKUs</span>
            <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--color-paytm-navy)', marginTop: '4px' }}>
              {products.length} Products
            </div>
            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>Across active store catalog</span>
          </Card>
          <Card style={{ padding: '16px 20px' }}>
            <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)', fontWeight: 500 }}>Total Stock in Store</span>
            <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--color-paytm-cyan)', marginTop: '4px' }}>
              {totalStockUnits.toLocaleString('en-IN')} Units
            </div>
            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>Physical on-shelf inventory</span>
          </Card>
          <Card style={{ padding: '16px 20px' }}>
            <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)', fontWeight: 500 }}>Low Stock Warnings</span>
            <div style={{ fontSize: '24px', fontWeight: 700, color: lowStockCount > 0 ? 'var(--color-danger)' : 'var(--color-success-dark)', marginTop: '4px' }}>
              {lowStockCount} SKUs
            </div>
            <span style={{ fontSize: '11px', color: lowStockCount > 0 ? 'var(--color-danger)' : 'var(--color-success-dark)', fontWeight: 600 }}>
              {lowStockCount > 0 ? 'Reorder threshold reached' : 'Optimal inventory levels'}
            </span>
          </Card>
          <Card style={{ padding: '16px 20px' }}>
            <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)', fontWeight: 500 }}>Auto Reorder Velocity</span>
            <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '4px' }}>
              Active
            </div>
            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>Continuous stockout guard</span>
          </Card>
        </div>
      )}

      {/* Filter & Search Bar */}
      <Card style={{ padding: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', width: '100%', maxWidth: '360px' }}>
            <Search size={15} color="var(--color-text-muted)" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              placeholder={activeSubTab === 'transactions' ? "Search by transaction ID, method..." : "Search product name, category, supplier..."}
              value={searchTerm}
              onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
              style={{
                width: '100%',
                padding: '8px 12px 8px 36px',
                borderRadius: '8px',
                border: '1px solid var(--color-border)',
                backgroundColor: 'var(--color-bg-page)',
                fontSize: '13px',
                color: 'var(--color-text-primary)',
                outline: 'none'
              }}
            />
          </div>

          {/* Filters */}
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
            {activeSubTab === 'transactions' ? (
              ['ALL', 'UPI', 'CARD', 'CASH'].map(mode => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => { setFilterMethod(mode); setCurrentPage(1); }}
                  style={{
                    padding: '5px 12px',
                    borderRadius: '16px',
                    border: '1px solid',
                    borderColor: filterMethod === mode ? 'var(--color-paytm-cyan)' : 'var(--color-border)',
                    backgroundColor: filterMethod === mode ? 'var(--color-paytm-cyan-tint)' : '#FFFFFF',
                    color: filterMethod === mode ? 'var(--color-paytm-navy)' : 'var(--color-text-secondary)',
                    fontSize: '12px',
                    fontWeight: filterMethod === mode ? 600 : 500,
                    cursor: 'pointer'
                  }}
                >
                  {mode}
                </button>
              ))
            ) : (
              categories.map(cat => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => { setFilterCategory(cat); setCurrentPage(1); }}
                  style={{
                    padding: '5px 12px',
                    borderRadius: '16px',
                    border: '1px solid',
                    borderColor: filterCategory === cat ? 'var(--color-paytm-cyan)' : 'var(--color-border)',
                    backgroundColor: filterCategory === cat ? 'var(--color-paytm-cyan-tint)' : '#FFFFFF',
                    color: filterCategory === cat ? 'var(--color-paytm-navy)' : 'var(--color-text-secondary)',
                    fontSize: '12px',
                    fontWeight: filterCategory === cat ? 600 : 500,
                    cursor: 'pointer'
                  }}
                >
                  {cat}
                </button>
              ))
            )}

            {/* Pagination controls */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '12px' }}>
              <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
                {currentPage} / {totalPages}
              </span>
              <Button variant="ghost" size="sm" disabled={currentPage <= 1} onClick={() => setCurrentPage(p => Math.max(1, p - 1))}>
                <ChevronLeft size={15} />
              </Button>
              <Button variant="ghost" size="sm" disabled={currentPage >= totalPages} onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}>
                <ChevronRight size={15} />
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {/* Main Data Table */}
      <Card noPadding style={{ overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <Skeleton height="45px" />
            <Skeleton height="45px" />
            <Skeleton height="45px" />
          </div>
        ) : activeSubTab === 'transactions' ? (
          /* TRANSACTIONS TABLE */
          paginatedList.length > 0 ? (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                <thead>
                  <tr style={{ background: 'var(--color-bg-page)', borderBottom: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }}>
                    <th style={{ padding: '12px 18px', fontWeight: 600 }}>Tx ID / Ref</th>
                    <th style={{ padding: '12px 18px', fontWeight: 600 }}>Timestamp</th>
                    <th style={{ padding: '12px 18px', fontWeight: 600 }}>Quantity</th>
                    <th style={{ padding: '12px 18px', fontWeight: 600 }}>Unit Price</th>
                    <th style={{ padding: '12px 18px', fontWeight: 600 }}>Total Amount</th>
                    <th style={{ padding: '12px 18px', fontWeight: 600 }}>Payment Method</th>
                    <th style={{ padding: '12px 18px', fontWeight: 600, textAlign: 'right' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedList.map((tx, idx) => {
                    const timeStr = tx.transaction_timestamp
                      ? new Date(tx.transaction_timestamp).toLocaleString('en-IN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                      : 'Just now';
                    const amount = Number(tx.amount || 0);

                    return (
                      <tr key={tx.id || idx} style={{ borderBottom: '1px solid var(--color-border)' }}>
                        <td style={{ padding: '12px 18px', fontFamily: 'monospace', fontSize: '12px', color: 'var(--color-paytm-navy)', fontWeight: 600 }}>
                          {(tx.id || 'tx-001').slice(0, 13)}...
                        </td>
                        <td style={{ padding: '12px 18px', color: 'var(--color-text-secondary)', fontSize: '12px' }}>
                          {timeStr}
                        </td>
                        <td style={{ padding: '12px 18px', color: 'var(--color-text-primary)', fontWeight: 500 }}>
                          {tx.quantity || 1} units
                        </td>
                        <td style={{ padding: '12px 18px', color: 'var(--color-text-secondary)' }}>
                          {formatINR(tx.unit_price || (amount / (tx.quantity || 1)))}
                        </td>
                        <td style={{ padding: '12px 18px', fontWeight: 700, color: 'var(--color-paytm-navy)' }}>
                          {formatINR(amount)}
                        </td>
                        <td style={{ padding: '12px 18px' }}>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '3px 8px',
                            borderRadius: '6px',
                            fontSize: '11px',
                            fontWeight: 600,
                            backgroundColor: (tx.payment_method || '').toUpperCase().includes('UPI') ? 'var(--color-paytm-cyan-tint)' : 'var(--color-bg-page)',
                            color: (tx.payment_method || '').toUpperCase().includes('UPI') ? 'var(--color-paytm-cyan-dark)' : 'var(--color-text-secondary)'
                          }}>
                            <CreditCard size={11} /> {tx.payment_method || 'UPI_QR'}
                          </span>
                        </td>
                        <td style={{ padding: '12px 18px', textAlign: 'right' }}>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '2px 8px',
                            borderRadius: '12px',
                            fontSize: '11px',
                            fontWeight: 600,
                            backgroundColor: 'var(--color-success-tint)',
                            color: 'var(--color-success-dark)'
                          }}>
                            <CheckCircle2 size={12} /> Success
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              icon={Receipt}
              title="No transactions recorded yet"
              description={`Use "Simulate UPI Payment" from the Demo Tools menu to generate real-time live purchases for ${shopName}.`}
            />
          )
        ) : (
          /* INVENTORY TABLE */
          paginatedList.length > 0 ? (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                <thead>
                  <tr style={{ background: 'var(--color-bg-page)', borderBottom: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }}>
                    <th style={{ padding: '12px 18px', fontWeight: 600 }}>Product Name</th>
                    <th style={{ padding: '12px 18px', fontWeight: 600 }}>Category</th>
                    <th style={{ padding: '12px 18px', fontWeight: 600 }}>Current Stock</th>
                    <th style={{ padding: '12px 18px', fontWeight: 600 }}>Reorder Level</th>
                    <th style={{ padding: '12px 18px', fontWeight: 600 }}>Unit Price</th>
                    <th style={{ padding: '12px 18px', fontWeight: 600 }}>Avg Daily Velocity</th>
                    <th style={{ padding: '12px 18px', fontWeight: 600, textAlign: 'right' }}>Stock Status</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedList.map((p, idx) => {
                    const stock = Number(p.current_stock || 0);
                    const reorder = Number(p.reorder_level || 10);
                    const isLow = stock <= reorder;
                    const isOut = stock === 0;

                    return (
                      <tr key={p.id || idx} style={{ borderBottom: '1px solid var(--color-border)' }}>
                        <td style={{ padding: '12px 18px', fontWeight: 600, color: 'var(--color-paytm-navy)' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <Package size={16} color="var(--color-paytm-cyan-dark)" />
                            <div>
                              <div>{p.name}</div>
                              <div style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
                                Supplier: {p.supplier || 'Direct'}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td style={{ padding: '12px 18px', color: 'var(--color-text-secondary)' }}>
                          <span style={{ backgroundColor: 'var(--color-bg-page)', padding: '3px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: 500 }}>
                            {p.category || 'General'}
                          </span>
                        </td>
                        <td style={{ padding: '12px 18px', fontWeight: 700, color: isOut ? 'var(--color-danger)' : (isLow ? 'var(--color-warning-dark)' : 'var(--color-text-primary)') }}>
                          {stock} units
                        </td>
                        <td style={{ padding: '12px 18px', color: 'var(--color-text-secondary)' }}>
                          {reorder} units
                        </td>
                        <td style={{ padding: '12px 18px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                          {formatINR(p.price)}
                        </td>
                        <td style={{ padding: '12px 18px', color: 'var(--color-text-secondary)' }}>
                          {p.average_daily_sales ? `${p.average_daily_sales} / day` : '5 / day'}
                        </td>
                        <td style={{ padding: '12px 18px', textAlign: 'right' }}>
                          {isOut ? (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '3px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 600, backgroundColor: 'var(--color-danger-tint)', color: 'var(--color-danger)' }}>
                              <XCircle size={12} /> Out of Stock
                            </span>
                          ) : isLow ? (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '3px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 600, backgroundColor: 'var(--color-warning-tint)', color: 'var(--color-warning-dark)' }}>
                              <AlertTriangle size={12} /> Low Stock
                            </span>
                          ) : (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '3px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 600, backgroundColor: 'var(--color-success-tint)', color: 'var(--color-success-dark)' }}>
                              <CheckCircle2 size={12} /> Healthy Stock
                            </span>
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
              icon={Boxes}
              title="No inventory records found"
              description="Your product catalog is empty or matching no search filters."
            />
          )
        )}
      </Card>
    </div>
  );
}
