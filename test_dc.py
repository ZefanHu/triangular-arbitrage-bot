import asyncio
from core.data_collector import DataCollector

async def main():
    dc = DataCollector()
    
    print("Starting DataCollector...")
    await dc.start()
    
    print("Waiting 5 seconds for initialization...")
    await asyncio.sleep(5)
    
    print("Getting orderbook...")
    orderbook = dc.get_orderbook('BTC-USDT')
    print(f"BTC-USDT orderbook: {orderbook}")
    
    print("Stopping DataCollector...")
    await dc.stop()
    
    print("Test completed!")

if __name__ == "__main__":
    asyncio.run(main())
