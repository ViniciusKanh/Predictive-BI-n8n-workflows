// Regras comerciais executadas no nó Code do n8n. Nenhuma chamada de rede ocorre aqui.
function calculateAnalytics(inputRows, filters = {}) {
  const rows = inputRows.filter(row => (!filters.start || row.order_date >= filters.start)
    && (!filters.end || row.order_date <= filters.end)
    && (!filters.category || row.category === filters.category)
    && (!filters.region || row.region === filters.region));
  if (!rows.length) return {empty:true,demonstrative:true,kpis:{},monthly:[],daily:[],categories:[],
    regions:[],products:[],channels:[],heatmap:[],orders:[],table_limit:2000,filters};
  let revenueCents = 0, completed = 0, cancelled = 0;
  const buyers = new Set(), paidBuyers = new Map(), months = new Map(), days = new Map();
  const categories = new Map(), regions = new Map(), products = new Map(), channels = new Map(), heat = new Map();
  let firstDate = rows[0].order_date, lastDate = firstDate;
  const add = (map, key, cents) => {
    if (!map.has(key)) map.set(key,{name:key,cents:0,orders:0});
    const value = map.get(key); value.cents += cents; value.orders++;
  };
  for (const row of rows) {
    const cents = row.revenue_cents;
    if (!Number.isSafeInteger(cents) || cents < 0) throw new Error('Receita inválida na fonte');
    revenueCents += cents;
    buyers.add(row.customer_id);
    if (row.order_date < firstDate) firstDate = row.order_date;
    if (row.order_date > lastDate) lastDate = row.order_date;
    if (row.status === 'completed') {
      completed++; paidBuyers.set(row.customer_id,(paidBuyers.get(row.customer_id)||0)+1);
    } else if (row.status === 'cancelled') cancelled++;
    const month = row.order_date.slice(0,7);
    if (!months.has(month)) months.set(month,{month,cents:0,orders:0,buyers:new Set()});
    const bucket = months.get(month); bucket.cents += cents; bucket.orders++; bucket.buyers.add(row.customer_id);
    add(days,row.order_date,cents); add(categories,row.category,cents); add(regions,row.region,cents);
    add(products,row.product,cents); add(channels,row.channel,cents);
    const weekday = (new Date(row.order_date+'T00:00:00Z').getUTCDay()+6)%7;
    const key = month+'/'+weekday;
    if (!heat.has(key)) heat.set(key,{month,weekday,cents:0});
    heat.get(key).cents += cents;
  }
  const monthly = [...months.values()].sort((a,b)=>a.month.localeCompare(b.month)).map(r=>({
    month:r.month,revenue:r.cents/100,orders:r.orders,customers:r.buyers.size,ticket:r.cents/100/r.orders}));
  const latest = monthly[monthly.length-1], previous = monthly[monthly.length-2];
  const aggregate = map => [...map.values()].sort((a,b)=>b.cents-a.cents||a.name.localeCompare(b.name)).map(r=>({
    name:r.name,revenue:r.cents/100,orders:r.orders}));
  const orderSample = [...rows].sort((a,b)=>b.order_date.localeCompare(a.order_date)||b.order_id-a.order_id).slice(0,2000);
  return {empty:false,demonstrative:true,
    kpis:{revenue:revenueCents/100,orders:rows.length,customers:buyers.size,
      ticket:completed?revenueCents/100/completed:0,cancel_rate:cancelled/rows.length*100,
      repeat_rate:paidBuyers.size?[...paidBuyers.values()].filter(n=>n>1).length/paidBuyers.size*100:0,
      monthly_growth:previous?.revenue?(latest.revenue/previous.revenue-1)*100:null,
      latest_month:latest.month,latest_month_revenue:latest.revenue,start:firstDate,end:lastDate,completed_orders:completed},
    monthly,daily:[...days.values()].sort((a,b)=>a.name.localeCompare(b.name)).map(r=>({order_date:r.name,revenue:r.cents/100,orders:r.orders})),
    categories:aggregate(categories),regions:aggregate(regions),products:aggregate(products),channels:aggregate(channels),
    heatmap:[...heat.values()].sort((a,b)=>a.month.localeCompare(b.month)||a.weekday-b.weekday).map(r=>({month:r.month,weekday:r.weekday,revenue:r.cents/100})),
    orders:orderSample.map(r=>({order_id:r.order_id,order_date:r.order_date,customer:r.customer,region:r.region,
      product:r.product,category:r.category,quantity:r.quantity,revenue:r.revenue_cents/100,status:r.status})),
    table_limit:2000,filters};
}

// O gerador inclui somente a função acima no Code node. Esta exportação serve aos testes locais.
if (typeof module !== 'undefined') module.exports = {calculateAnalytics};
