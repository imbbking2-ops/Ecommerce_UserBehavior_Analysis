from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR.parent / "docs" / "images" / "sql"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WIDTH, HEIGHT = 1500, 820
BG = "#F7F9FC"
NAVY = "#17324D"
BLUE = "#2878B5"
TEAL = "#2A9D8F"
ORANGE = "#F4A261"
RED = "#E76F51"
GRID = "#D8E1EA"
MUTED = "#60758A"
WHITE = "#FFFFFF"

FONT_PATH = Path("C:/Windows/Fonts/segoeui.ttf")
BOLD_PATH = Path("C:/Windows/Fonts/seguisb.ttf")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(BOLD_PATH if bold else FONT_PATH), size)


def canvas(title: str, subtitle: str = ""):
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.text((70, 48), title, fill=NAVY, font=font(38, True))
    if subtitle:
        draw.text((72, 102), subtitle, fill=MUTED, font=font(19))
    return image, draw


def save(image: Image.Image, filename: str) -> None:
    image.save(OUTPUT_DIR / filename, quality=95)


def read_rows(number: int) -> list[dict[str, str]]:
    with (BASE_DIR / f"{number}.csv").open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def number(value: str) -> str:
    try:
        numeric = float(value)
        if numeric.is_integer():
            return f"{int(numeric):,}"
        return f"{numeric:,.2f}"
    except (TypeError, ValueError):
        return value


def table_image(number_id: int, title: str) -> None:
    rows = read_rows(number_id)
    columns = list(rows[0])
    image, draw = canvas(title, f"Source: sql_result/{number_id}.csv")
    left, top, right = 70, 170, WIDTH - 70
    column_width = (right - left) / len(columns)
    row_height = min(78, 520 / max(1, len(rows) + 1))

    for index, column in enumerate(columns):
        x0 = left + index * column_width
        x1 = left + (index + 1) * column_width
        draw.rounded_rectangle(
            (x0 + 2, top, x1 - 2, top + row_height),
            radius=7,
            fill=NAVY,
        )
        label = column.replace("_", " ").title()
        box = draw.textbbox((0, 0), label, font=font(18, True))
        draw.text(
            ((x0 + x1 - (box[2] - box[0])) / 2, top + 20),
            label,
            fill=WHITE,
            font=font(18, True),
        )

    for row_index, row in enumerate(rows, start=1):
        y0 = top + row_index * row_height
        y1 = y0 + row_height - 3
        fill = "#EAF1F7" if row_index % 2 else "#F1F5F9"
        for column_index, column in enumerate(columns):
            x0 = left + column_index * column_width
            x1 = left + (column_index + 1) * column_width
            draw.rounded_rectangle((x0 + 2, y0, x1 - 2, y1), radius=6, fill=fill)
            text = number(row[column])
            box = draw.textbbox((0, 0), text, font=font(18))
            draw.text(
                ((x0 + x1 - (box[2] - box[0])) / 2, y0 + 18),
                text,
                fill=NAVY,
                font=font(18),
            )
    save(image, f"{number_id:02d}_sql_result.png")


def line_chart(
    title: str,
    subtitle: str,
    x_labels: list[str],
    series: list[tuple[str, list[float], str]],
    filename: str,
) -> None:
    image, draw = canvas(title, subtitle)
    plot = (105, 170, WIDTH - 70, HEIGHT - 105)
    x0, y0, x1, y1 = plot
    all_values = [value for _, values, _ in series for value in values]
    maximum = max(all_values) if all_values else 1

    for step in range(6):
        y = y1 - (y1 - y0) * step / 5
        draw.line((x0, y, x1, y), fill=GRID, width=2)
        label = f"{maximum * step / 5:,.0f}"
        draw.text((20, y - 11), label, fill=MUTED, font=font(15))

    count = max(1, len(x_labels) - 1)
    for label_index, label in enumerate(x_labels):
        if len(x_labels) > 12 and label_index % max(1, len(x_labels) // 8):
            continue
        x = x0 + (x1 - x0) * label_index / count
        draw.text((x - 28, y1 + 18), label, fill=MUTED, font=font(14))

    for name, values, color in series:
        points = []
        for index, value in enumerate(values):
            x = x0 + (x1 - x0) * index / count
            y = y1 - (y1 - y0) * value / maximum
            points.append((x, y))
        if len(points) > 1:
            draw.line(points, fill=color, width=5, joint="curve")
        for point in points:
            draw.ellipse((point[0] - 4, point[1] - 4, point[0] + 4, point[1] + 4), fill=color)

    legend_x = x0
    for name, _, color in series:
        draw.line((legend_x, 140, legend_x + 35, 140), fill=color, width=5)
        draw.text((legend_x + 45, 127), name, fill=NAVY, font=font(17))
        legend_x += 210
    save(image, filename)


def daily_traffic() -> None:
    rows = read_rows(3)
    line_chart(
        "Daily Traffic Trend",
        "Total activity, page views and unique users by date",
        [row["behavior_date"][5:] for row in rows],
        [
            ("Total events", [float(row["event_count"]) for row in rows], BLUE),
            ("PV events", [float(row["pv_events"]) for row in rows], TEAL),
            ("Unique users", [float(row["uv"]) for row in rows], ORANGE),
        ],
        "03_daily_traffic.png",
    )


def hourly_traffic() -> None:
    rows = read_rows(5)
    line_chart(
        "Hourly Traffic Pattern",
        "Activity distribution across the 24-hour cycle",
        [row["behavior_hour"] for row in rows],
        [
            ("Total events", [float(row["event_count"]) for row in rows], BLUE),
            ("PV", [float(row["pv"]) for row in rows], TEAL),
            ("Active users", [float(row["active_users"]) for row in rows], ORANGE),
            ("Buy events", [float(row["buy_events"]) for row in rows], RED),
        ],
        "05_hourly_traffic.png",
    )


def heatmap(number_id: int, time_column: str, title: str, filename: str) -> None:
    totals: dict[int, int] = defaultdict(int)
    cells: dict[tuple[int, str], int] = defaultdict(int)
    times: set[str] = set()
    with (BASE_DIR / f"{number_id}.csv").open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            item = int(row["item_id"])
            period = row[time_column]
            value = int(row["event_count"])
            totals[item] += value
            cells[(item, period)] += value
            times.add(period)

    top_items = [item for item, _ in sorted(totals.items(), key=lambda pair: pair[1], reverse=True)[:10]]
    if time_column == "behavior_hour":
        periods = [str(hour) for hour in range(24)]
    else:
        periods = sorted(times)

    image, draw = canvas(title, "Top 10 items ranked by total event count")
    left, top, right, bottom = 180, 180, WIDTH - 80, HEIGHT - 105
    cell_width = (right - left) / len(periods)
    cell_height = (bottom - top) / len(top_items)
    maximum = max((cells[(item, period)] for item in top_items for period in periods), default=1)

    for row_index, item in enumerate(top_items):
        y0 = top + row_index * cell_height
        draw.text((55, y0 + cell_height / 2 - 10), str(item), fill=NAVY, font=font(16))
        for column_index, period in enumerate(periods):
            value = cells[(item, period)]
            intensity = value / maximum
            if number_id == 4:
                color = (
                    int(235 - 170 * intensity),
                    int(244 - 105 * intensity),
                    int(250 - 65 * intensity),
                )
            else:
                color = (
                    255,
                    int(242 - 155 * intensity),
                    int(204 - 145 * intensity),
                )
            x0 = left + column_index * cell_width
            draw.rectangle(
                (x0 + 1, y0 + 1, x0 + cell_width - 1, y0 + cell_height - 1),
                fill=color,
            )

    label_step = max(1, len(periods) // 10)
    for index, period in enumerate(periods):
        if index % label_step:
            continue
        label = period[5:] if time_column == "behavior_date" else period
        x = left + index * cell_width
        draw.text((x, bottom + 17), label, fill=MUTED, font=font(14))
    draw.text((70, 145), "Item ID", fill=MUTED, font=font(16))
    draw.text((left, bottom + 55), "Date" if number_id == 4 else "Hour of day", fill=NAVY, font=font(17, True))
    save(image, filename)


def category_analysis() -> None:
    rows = read_rows(10)
    image, draw = canvas(
        "Top 20 Product Categories by Purchases",
        "Bar length represents purchase count; labels also show purchase-to-PV rate",
    )
    left, top, right, bottom = 245, 165, WIDTH - 90, HEIGHT - 55
    max_count = max(int(row["buy_count"]) for row in rows)
    row_height = (bottom - top) / len(rows)

    for index, row in enumerate(rows):
        y = top + index * row_height
        count = int(row["buy_count"])
        rate = float(row["buy_pv_rate"])
        width = (right - left) * count / max_count
        draw.text(
            (55, y + 5),
            str(row["category_id"]),
            fill=NAVY,
            font=font(15),
        )
        draw.rounded_rectangle(
            (left, y + 3, left + width, y + row_height - 5),
            radius=7,
            fill=BLUE if rate < 3 else TEAL,
        )
        label = f"{count:,} buys  |  {rate:.2f}%"
        label_box = draw.textbbox((0, 0), label, font=font(15, True))
        label_width = label_box[2] - label_box[0]
        if left + width + label_width + 14 <= right:
            label_x = left + width + 12
            label_color = NAVY
        else:
            label_x = left + width - label_width - 12
            label_color = WHITE
        draw.text(
            (label_x, y + 5),
            label,
            fill=label_color,
            font=font(15, True),
        )

    draw.text((55, 133), "Category ID", fill=MUTED, font=font(16))
    draw.text((left, bottom + 7), "Purchase count", fill=NAVY, font=font(17, True))
    save(image, "10_category_analysis.png")


def main() -> None:
    table_image(1, "Dataset Overview")
    table_image(2, "Behavior Distribution")
    daily_traffic()
    heatmap(4, "behavior_date", "Daily Traffic Heatmap — Top 10 Items", "04_product_daily_heatmap.png")
    hourly_traffic()
    heatmap(6, "behavior_hour", "Hourly Traffic Heatmap — Top 10 Items", "06_product_hourly_heatmap.png")
    table_image(7, "Valid Behavior-to-Purchase Conversion")
    table_image(8, "Repeat Purchase Summary")
    table_image(9, "RF User Segmentation")
    category_analysis()
    print(f"Generated 10 images in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
