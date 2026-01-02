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

        prev_time = 0
        for label, lap_time in self.laps:
            delta = lap_time - prev_time
            print(f"    {label:.<50}  {delta:>8.2f}s")
            prev_time = lap_time

        print("\n" + "-" * 100)
        print(f"    {'TOTAL TIME':.<50} {total:>8.2f}s")
        print("\n" + "=" * 100)

        return total

        
