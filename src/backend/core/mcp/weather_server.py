"""
内置天气 MCP 服务器 - 基于 Open-Meteo API（免费，无需 API Key）
"""
import json
import sys
import urllib.request
import urllib.parse
from typing import Any


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


TOOLS = {
    "geocode": {
        "description": "根据城市名称搜索地理坐标（纬度、经度）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "城市名称（中文或英文）"}
            },
            "required": ["name"]
        }
    },
    "get_weather": {
        "description": "获取指定城市的当前天气和未来几天的天气预报",
        "inputSchema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名称（中文或英文）"},
                "days": {"type": "integer", "description": "预报天数（1-7，默认3）", "default": 3}
            },
            "required": ["city"]
        }
    }
}


def _http_get(url: str) -> dict:
    """Simple HTTP GET returning JSON."""
    req = urllib.request.Request(url, headers={"User-Agent": "PersBot-Weather/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def _geocode(name: str) -> list:
    """Geocode city name to coordinates."""
    params = urllib.parse.urlencode({"name": name, "count": 3, "language": "zh"})
    data = _http_get(f"{GEOCODING_URL}?{params}")
    return data.get("results", [])


def handle_geocode(arguments: dict) -> str:
    name = arguments.get("name", "")
    results = _geocode(name)
    if not results:
        return f"未找到城市: {name}"
    lines = []
    for r in results:
        lines.append(f"- {r['name']} ({r.get('admin1', '')}, {r.get('country', '')}): "
                      f"纬度 {r['latitude']}, 经度 {r['longitude']}")
    return "\n".join(lines)


def handle_get_weather(arguments: dict) -> str:
    city = arguments.get("city", "")
    days = min(arguments.get("days", 3), 7)

    # Step 1: geocode
    results = _geocode(city)
    if not results:
        return f"未找到城市: {city}"

    loc = results[0]
    lat, lon = loc["latitude"], loc["longitude"]
    city_name = f"{loc['name']}"
    if loc.get("admin1"):
        city_name += f", {loc['admin1']}"

    # Step 2: get forecast
    params = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
        "forecast_days": days,
        "timezone": "auto"
    })
    data = _http_get(f"{FORECAST_URL}?{params}")

    lines = [f"📍 {city_name}\n"]

    # Current weather
    current = data.get("current", {})
    if current:
        wcode = current.get("weather_code", 0)
        lines.append(f"🌡️ 当前天气:")
        lines.append(f"  温度: {current.get('temperature_2m', 'N/A')}°C")
        lines.append(f"  湿度: {current.get('relative_humidity_2m', 'N/A')}%")
        lines.append(f"  天气: {_weather_desc(wcode)}")
        lines.append(f"  风速: {current.get('wind_speed_10m', 'N/A')} km/h")
        lines.append("")

    # Daily forecast
    daily = data.get("daily", {})
    dates = daily.get("time", [])
    if dates:
        lines.append(f"📅 未来{len(dates)}天预报:")
        for i, date in enumerate(dates):
            wcode = daily.get("weather_code", [0])[i] if i < len(daily.get("weather_code", [])) else 0
            t_max = daily.get("temperature_2m_max", [None])[i]
            t_min = daily.get("temperature_2m_min", [None])[i]
            precip = daily.get("precipitation_sum", [0])[i]
            wind = daily.get("wind_speed_10m_max", [None])[i]
            lines.append(f"  {date}: {_weather_desc(wcode)}, "
                         f"{t_min}°C ~ {t_max}°C, "
                         f"降水 {precip}mm, 最大风速 {wind}km/h")

    return "\n".join(lines)


def _weather_desc(code: int) -> str:
    """WMO weather code to Chinese description."""
    mapping = {
        0: "晴", 1: "大部晴", 2: "多云", 3: "阴",
        45: "雾", 48: "霜雾",
        51: "小毛毛雨", 53: "毛毛雨", 55: "大毛毛雨",
        61: "小雨", 63: "中雨", 65: "大雨",
        71: "小雪", 73: "中雪", 75: "大雪",
        80: "阵雨", 81: "中阵雨", 82: "大阵雨",
        85: "小阵雪", 86: "大阵雪",
        95: "雷暴", 96: "雷暴伴小冰雹", 99: "雷暴伴大冰雹",
    }
    return mapping.get(code, f"天气代码{code}")


HANDLERS = {
    "geocode": handle_geocode,
    "get_weather": handle_get_weather,
}


def send_json(obj: Any):
    """Write a JSON-RPC message to stdout."""
    line = json.dumps(obj, ensure_ascii=False) + "\n"
    sys.stdout.write(line)
    sys.stdout.flush()


def main():
    """Minimal JSON-RPC stdio MCP server."""
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = msg.get("method")
        msg_id = msg.get("id")

        if method == "initialize":
            send_json({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "persbot-weather", "version": "1.0.0"}
                }
            })
        elif method == "notifications/initialized":
            pass  # no response needed
        elif method == "tools/list":
            tools_list = [
                {"name": name, "description": info["description"], "inputSchema": info["inputSchema"]}
                for name, info in TOOLS.items()
            ]
            send_json({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools_list}})
        elif method == "tools/call":
            params = msg.get("params", {})
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            handler = HANDLERS.get(tool_name)
            if handler:
                try:
                    text = handler(arguments)
                    send_json({
                        "jsonrpc": "2.0", "id": msg_id,
                        "result": {"content": [{"type": "text", "text": text}]}
                    })
                except Exception as e:
                    send_json({
                        "jsonrpc": "2.0", "id": msg_id,
                        "result": {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True}
                    })
            else:
                send_json({
                    "jsonrpc": "2.0", "id": msg_id,
                    "error": {"code": -32602, "message": f"Unknown tool: {tool_name}"}
                })
        elif msg_id is not None:
            send_json({
                "jsonrpc": "2.0", "id": msg_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            })


if __name__ == "__main__":
    main()
