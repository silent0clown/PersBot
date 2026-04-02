import asyncio
import logging
from core.mcp import MCPManager, MCPServerInfo

logging.basicConfig(level=logging.DEBUG)

async def test():
    servers = [
        MCPServerInfo(
            name='weather',
            enabled=True,
            command='npx',
            args=['-y', '@dangahagan/weather-mcp'],
            env={},
            url=None
        )
    ]
    manager = MCPManager(servers)
    await manager.initialize()
    print('Connected servers:', manager.get_connected_servers())
    print('Tools:', manager.list_tools())

if __name__ == '__main__':
    asyncio.run(test())