/*
 * Windows x64 PE/COFF linker-script supplement.
 *
 * Keep native game-owned sections distinct for save-state ownership, as the
 * Linux linker script does. Unlike ELF, PE requires every output section
 * VirtualAddress to be a multiple of SectionAlignment (normally 0x1000).
 * The unaligned native script produced nonconforming game_data/game_bss
 * sections, which Windows can reject before executing the process.
 *
 * The Linux linker script is not changed; this file fixes PE layout only.
 */
SECTIONS
{
    game_data ALIGN(0x1000) :
    {
        __start_game_data = .;
        *(gba_data)
        __stop_game_data = .;
    }

    game_bss ALIGN(0x1000) :
    {
        __start_game_bss = .;
        *src/*.o(EXCLUDE_FILE (*src/*/*.o) .bss)
        *data/*.o(.bss)
        __stop_game_bss = .;
    }
}

INSERT AFTER .data;
