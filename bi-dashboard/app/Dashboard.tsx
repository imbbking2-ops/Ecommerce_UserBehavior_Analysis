"use client";

import { useMemo, useState } from "react";
import data from "./dashboard-data.json";

const formatNumber = (value: number) =>
  new Intl.NumberFormat("zh-CN").format(value);

const compactNumber = (value: number) =>
  new Intl.NumberFormat("zh-CN", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);

const behaviorColors: Record<string, string> = {
  pv: "#7c5cff",
  fav: "#ec6e9a",
  cart: "#e7a33e",
  buy: "#25a979",
};

export default function Dashboard() {
  const [selectedItem, setSelectedItem] = useState(
    String(data.topItems[0]?.item_id ?? ""),
  );
  const [metric, setMetric] = useState<"pv" | "event_count" | "buy">("pv");

  const maxDaily = Math.max(...data.daily.map((item) => item[metric]), 1);
  const maxHourly = Math.max(...data.hourly.map((item) => item.event_count), 1);
  const maxCategory = Math.max(
    ...data.topCategories.map((item) => item.event_count),
    1,
  );

  const selectedItemData = useMemo(
    () =>
      data.topItems.find((item) => String(item.item_id) === selectedItem) ??
      data.topItems[0],
    [selectedItem],
  );

  const itemDaily = useMemo(
    () =>
      data.topItemDaily.filter(
        (item) => String(item.item_id) === selectedItem,
      ),
    [selectedItem],
  );

  const itemHourly = useMemo(
    () =>
      data.topItemHourly.filter(
        (item) => String(item.item_id) === selectedItem,
      ),
    [selectedItem],
  );

  const maxItemDaily = Math.max(
    ...itemDaily.map((item) => item.event_count),
    1,
  );
  const maxItemHourly = Math.max(
    ...itemHourly.map((item) => item.event_count),
    1,
  );

  const metricLabels = {
    pv: "浏览量",
    event_count: "总行为",
    buy: "购买量",
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-mark">CP</div>
        <nav aria-label="看板导航">
          <a className="nav-item active" href="#overview" aria-label="经营概览">
            ◫
          </a>
          <a className="nav-item" href="#traffic" aria-label="流量趋势">
            ↗
          </a>
          <a className="nav-item" href="#conversion" aria-label="转化分析">
            ◎
          </a>
          <a className="nav-item" href="#products" aria-label="商品分析">
            ◇
          </a>
        </nav>
        <div className="sidebar-foot">BI</div>
      </aside>

      <main className="dashboard">
        <header className="topbar">
          <div>
            <p className="eyebrow">COMMERCE PULSE / 经营驾驶舱</p>
            <h1>用户行为分析</h1>
          </div>
          <div className="topbar-actions">
            <span className="status-dot">数据已同步</span>
            <div className="date-chip">
              {data.dateRange.start} — {data.dateRange.end}
            </div>
          </div>
        </header>

        <section className="hero" id="overview">
          <div className="hero-copy">
            <span className="section-tag">全局概览</span>
            <h2>
              把每一次行为，
              <br />
              变成可行动的增长信号。
            </h2>
            <p>
              从 {formatNumber(data.overview.totalEvents)} 条真实行为记录中，
              识别流量节奏、转化效率与高潜商品。
            </p>
          </div>
          <div className="hero-orbit" aria-label="购买转化概览">
            <div className="orbit-ring ring-one" />
            <div className="orbit-ring ring-two" />
            <div className="orbit-core">
              <span>购买事件</span>
              <strong>{compactNumber(data.overview.buyEvents)}</strong>
              <small>
                {(
                  (data.overview.buyEvents / data.overview.totalEvents) *
                  100
                ).toFixed(2)}
                % 行为占比
              </small>
            </div>
          </div>
        </section>

        <section className="kpi-grid" aria-label="核心指标">
          {[
            ["总行为量", data.overview.totalEvents, "全站行为事件", "01"],
            ["活跃用户", data.overview.totalUsers, "去重用户数", "02"],
            ["覆盖商品", data.overview.totalItems, "去重商品数", "03"],
            ["复购率", data.overview.repeatBuyRate, "购买两次及以上", "04"],
          ].map(([label, value, note, index]) => (
            <article className="kpi-card" key={String(label)}>
              <div className="kpi-top">
                <span>{index}</span>
                <i />
              </div>
              <strong>
                {label === "复购率"
                  ? `${Number(value).toFixed(2)}%`
                  : compactNumber(Number(value))}
              </strong>
              <h3>{label}</h3>
              <p>{note}</p>
            </article>
          ))}
        </section>

        <section className="content-grid" id="traffic">
          <article className="panel trend-panel">
            <div className="panel-header">
              <div>
                <span className="section-tag">日流量</span>
                <h2>行为趋势</h2>
              </div>
              <div className="segmented" role="group" aria-label="趋势指标">
                {(["pv", "event_count", "buy"] as const).map((item) => (
                  <button
                    className={metric === item ? "selected" : ""}
                    key={item}
                    onClick={() => setMetric(item)}
                  >
                    {metricLabels[item]}
                  </button>
                ))}
              </div>
            </div>
            <div className="bar-chart" aria-label={`${metricLabels[metric]}日趋势`}>
              {data.daily.map((item) => (
                <div className="bar-column" key={item.date}>
                  <span className="bar-value">{compactNumber(item[metric])}</span>
                  <div
                    className="bar"
                    style={{
                      height: `${Math.max((item[metric] / maxDaily) * 100, 3)}%`,
                    }}
                  />
                  <small>{item.date.slice(5)}</small>
                </div>
              ))}
            </div>
          </article>

          <article className="panel behavior-panel">
            <div className="panel-header">
              <div>
                <span className="section-tag">行为结构</span>
                <h2>用户在做什么</h2>
              </div>
              <span className="panel-index">A / 04</span>
            </div>
            <div className="behavior-stack" aria-label="行为占比">
              {data.behaviorDistribution.map((item) => (
                <span
                  key={item.behavior}
                  style={{
                    width: `${item.ratio}%`,
                    background: behaviorColors[item.behavior],
                  }}
                  title={`${item.label} ${item.ratio}%`}
                />
              ))}
            </div>
            <div className="behavior-list">
              {data.behaviorDistribution.map((item) => (
                <div className="behavior-row" key={item.behavior}>
                  <i style={{ background: behaviorColors[item.behavior] }} />
                  <span>{item.label}</span>
                  <strong>{compactNumber(item.count)}</strong>
                  <em>{item.ratio}%</em>
                </div>
              ))}
            </div>
          </article>
        </section>

        <section className="panel hour-panel">
          <div className="panel-header">
            <div>
              <span className="section-tag">小时流量</span>
              <h2>一天中的活跃节奏</h2>
            </div>
            <p>颜色越深，行为越集中</p>
          </div>
          <div className="hour-grid">
            {data.hourly.map((item) => {
              const intensity = 0.12 + (item.event_count / maxHourly) * 0.88;
              return (
                <div className="hour-cell" key={item.hour}>
                  <div
                    style={{ opacity: intensity }}
                    title={`${item.hour}:00 · ${formatNumber(item.event_count)} 次`}
                  />
                  <strong>{String(item.hour).padStart(2, "0")}</strong>
                  <small>{compactNumber(item.event_count)}</small>
                </div>
              );
            })}
          </div>
        </section>

        <section className="conversion-section" id="conversion">
          <div className="section-heading">
            <div>
              <span className="section-tag light">行为 → 购买</span>
              <h2>哪一步最接近成交？</h2>
            </div>
            <p>
              同一用户、同一商品，且购买发生在行为之后，才计为有效转化。
            </p>
          </div>
          <div className="conversion-grid">
            {data.conversion.map((item, index) => (
              <article className="conversion-card" key={item.behavior_type}>
                <span>0{index + 1}</span>
                <h3>{item.label}后购买</h3>
                <strong>{item.rate.toFixed(2)}%</strong>
                <div className="conversion-track">
                  <i style={{ width: `${Math.min(item.rate * 10, 100)}%` }} />
                </div>
                <p>
                  {formatNumber(item.converted)} / {formatNumber(item.total)}{" "}
                  条行为有效转化
                </p>
              </article>
            ))}
            <article className="conversion-note">
              <span className="note-kicker">INSIGHT</span>
              <strong>加购是当前最强的成交前置信号。</strong>
              <p>
                加购后购买转化率比浏览后高{" "}
                {(
                  data.conversion.find((item) => item.behavior_type === "cart")!
                    .rate /
                  data.conversion.find((item) => item.behavior_type === "pv")!
                    .rate
                ).toFixed(1)}
                倍。
              </p>
            </article>
          </div>
        </section>

        <section className="products-section" id="products">
          <div className="section-heading dark">
            <div>
              <span className="section-tag">商品流量</span>
              <h2>高热商品雷达</h2>
            </div>
            <div className="item-picker">
              <label htmlFor="item-select">查看商品</label>
              <select
                id="item-select"
                value={selectedItem}
                onChange={(event) => setSelectedItem(event.target.value)}
              >
                {data.topItems.map((item) => (
                  <option key={item.item_id} value={String(item.item_id)}>
                    商品 {item.item_id}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="product-layout">
            <article className="panel product-profile">
              <span className="rank-badge">TOP ITEM</span>
              <h3>商品 {selectedItemData?.item_id}</h3>
              <p>类目 {selectedItemData?.category_id}</p>
              <div className="product-stat-grid">
                <div>
                  <span>总行为</span>
                  <strong>{compactNumber(selectedItemData?.event_count ?? 0)}</strong>
                </div>
                <div>
                  <span>访客</span>
                  <strong>{compactNumber(selectedItemData?.uv ?? 0)}</strong>
                </div>
                <div>
                  <span>浏览</span>
                  <strong>{compactNumber(selectedItemData?.pv ?? 0)}</strong>
                </div>
                <div>
                  <span>购买</span>
                  <strong>{compactNumber(selectedItemData?.buy ?? 0)}</strong>
                </div>
              </div>
            </article>

            <article className="panel mini-trend">
              <div className="mini-header">
                <h3>商品日流量</h3>
                <span>按日</span>
              </div>
              <div className="mini-bars">
                {itemDaily.map((item) => (
                  <div key={item.date}>
                    <i
                      style={{
                        height: `${Math.max(
                          (item.event_count / maxItemDaily) * 100,
                          4,
                        )}%`,
                      }}
                    />
                    <small>{item.date.slice(8)}</small>
                  </div>
                ))}
              </div>
            </article>

            <article className="panel mini-trend">
              <div className="mini-header">
                <h3>商品小时流量</h3>
                <span>0—23 时</span>
              </div>
              <div className="mini-bars hourly">
                {itemHourly.map((item) => (
                  <div key={item.hour}>
                    <i
                      style={{
                        height: `${Math.max(
                          (item.event_count / maxItemHourly) * 100,
                          3,
                        )}%`,
                      }}
                    />
                    <small>{item.hour % 3 === 0 ? item.hour : ""}</small>
                  </div>
                ))}
              </div>
            </article>
          </div>

          <div className="table-panel">
            <div className="table-head">
              <h3>商品热度排行</h3>
              <span>按总行为量排序</span>
            </div>
            <div className="data-table" role="table" aria-label="商品排行">
              <div className="table-row header" role="row">
                <span>排名</span>
                <span>商品 ID</span>
                <span>总行为</span>
                <span>UV</span>
                <span>加购</span>
                <span>购买</span>
              </div>
              {data.topItems.map((item, index) => (
                <button
                  className={`table-row ${
                    String(item.item_id) === selectedItem ? "active" : ""
                  }`}
                  key={item.item_id}
                  onClick={() => setSelectedItem(String(item.item_id))}
                  role="row"
                >
                  <span>0{index + 1}</span>
                  <strong>{item.item_id}</strong>
                  <span>{formatNumber(item.event_count)}</span>
                  <span>{formatNumber(item.uv)}</span>
                  <span>{formatNumber(item.cart)}</span>
                  <span>{formatNumber(item.buy)}</span>
                </button>
              ))}
            </div>
          </div>
        </section>

        <section className="category-section">
          <div className="section-heading dark">
            <div>
              <span className="section-tag">类目洞察</span>
              <h2>流量集中在哪里</h2>
            </div>
            <p>Top 10 类目 · 按行为量排序</p>
          </div>
          <div className="category-list">
            {data.topCategories.map((item, index) => (
              <div className="category-row" key={item.category_id}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <strong>类目 {item.category_id}</strong>
                <div>
                  <i
                    style={{
                      width: `${(item.event_count / maxCategory) * 100}%`,
                    }}
                  />
                </div>
                <em>{compactNumber(item.event_count)}</em>
              </div>
            ))}
          </div>
        </section>

        <footer>
          <span>COMMERCE PULSE</span>
          <p>
            数据范围 {data.dateRange.start} 至 {data.dateRange.end} ·
            指标快照由清洗数据生成
          </p>
        </footer>
      </main>
    </div>
  );
}
