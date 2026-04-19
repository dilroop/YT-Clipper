from PIL import ImageFont

def find_good_sizes():
    mac_path = "/System/Library/Fonts/Apple Color Emoji.ttc"
    # Testing a range of likely Apple bitmap sizes
    # Typical Apple sizes: 20, 32, 40, 48, 64, 96, 160, 256
    sizes_to_test = [20, 24, 32, 40, 48, 52, 64, 72, 80, 96, 120, 144, 160]
    for size in sizes_to_test:
        try:
            ImageFont.truetype(mac_path, size)
            print(f"Good size: {size}")
        except:
            pass

if __name__ == "__main__":
    find_good_sizes()
