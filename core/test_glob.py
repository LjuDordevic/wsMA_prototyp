from glob import iglob
from pathlib import Path 

test_dir = Path("/home/ljd/testglob")

stern_pattern = str(test_dir / "*/**")
negation_pattern = str(test_dir / "[!cde].*")
frage_pattern = str(test_dir / "e?*")

result = sorted(iglob(stern_pattern))
#result = sorted(iglob(stern_pattern, recursive=True))
#result = sorted(iglob(negation_pattern))
#result = sorted(iglob(frage_pattern))
#result = sorted(iglob("~/testglob/*"))

print(len(result))
for element in result:
    print(f"result: {element}")

