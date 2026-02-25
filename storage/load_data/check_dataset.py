from datasets import load_dataset

print("📦 Loading dataset...\n")
dataset = load_dataset("ashraq/fashion-product-images-small", split="train")

print(f"✅ Loaded {len(dataset)} items\n")

# Look at first item
first_item = dataset[0]

print("🔍 First item fields:")
for key in first_item.keys():
    print(f"   • {key}: {type(first_item[key])}")

print("\n📊 First item data:")
print(first_item)