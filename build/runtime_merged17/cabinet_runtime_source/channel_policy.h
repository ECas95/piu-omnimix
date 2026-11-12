// Category ownership follows the media song's original release, independently
// of the source of its latest chart revision.
static unsigned version_channel(unsigned v)
{
    static const unsigned ids[32] = {0x2f, 0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3a, 0x3b, 0x3c, 0x3d, 0x3e, 0x3f, 0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0x4a, 0x4b, 0x4c, 0x4d, 0x4e};
    return v >= 0x17 && v <= 0x36 ? ids[v - 0x17] : 0;
}
static unsigned chart_owner(const uint32_t *song, int count, const uint32_t *chart)
{
    unsigned lo = chart[0] & 0xffff, hi = chart[0] >> 16;
    if (!lo || !hi || lo >= (unsigned)count || hi >= (unsigned)count)
        return 0;
    // Ownership follows the media song even for native Mission/Train helpers.
    return version_channel(song[hi * 9 + 5] & 0xff);
}
static int basic_alias(const uint32_t *song, const uint32_t *c)
{
    unsigned lo=c[0]&0xffff, hi=c[0]>>16;
    return lo!=hi && (song[lo*9]&0xe0000000u)==0xe0000000u &&
           (song[hi*9+5]&0x01000000u);
}
static void apply_channel_policy(uint32_t *song, int song_count,
                                 uint32_t *chart, int chart_count, unsigned channel,
                                 int basic_context, int full_mode)
{
    for (int i = 1; i < chart_count; i++) {
        uint32_t *c = chart + i * 9;
        unsigned lo = c[0] & 0xffff, hi = c[0] >> 16;
        if (!lo || !hi || lo >= (unsigned)song_count || hi >= (unsigned)song_count)
            continue;
        unsigned owner = chart_owner(song, song_count, c);
        uint8_t *flags = (uint8_t *)c + 10;
        if (owner && lo!=hi) {
            *flags &= 0x7f; // Imported helper projections are not playable stock categories.
            continue;
        }
        if (basic_alias(song,c)) {
            if (!basic_context || owner) *flags &= 0x7f;
            continue;
        }
        // Basic Mode reads its helper projection. Full Mode reads the primary
        // records; their chart bytes are identical and neither view duplicates.
        if (basic_context && !owner && (song[(c[0]>>16)*9+5]&0x01000000u)) {
            *flags &= 0x7f;
            continue;
        }
        if (!owner && channel < 0x2f)
            continue;
        *flags &= 0x7f;
        // XIDDY is retired; IDOLMASTER/LOVE LIVE songs now belong to Anime.
        // Retired channel IDs are never reassigned.
        if (full_mode && owner && owner != 0x39 && owner != 0x3a && owner != 0x3c && owner == channel && c[1] != UINT32_MAX &&
            !(song[lo * 9 + 5] & 0x80000000u) && !(song[hi * 9 + 5] & 0x80000000u))
            *flags |= 0x80;
    }
}
