import time 

class TransformTimer:
    def __init__(self):
        self.start_time = time.time()
        self.laps = []        

    def lap(self, label):
        now = time.time()
        elapsed = now - self.start_time
        self.laps.append((label, elapsed))
        return elapsed
    
    def stop(self):
        total = time.time() - self.start_time

        print("\n" + "=" * 100)
        print("TIMER REPORT:")
        print("\n" + "=" * 100)

        return total

        
