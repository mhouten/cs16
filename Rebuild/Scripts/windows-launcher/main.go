// A windowless launcher for the portable Windows package.
package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
	"unsafe"
)

func main() {
	self, err := os.Executable()
	if err != nil {
		fail("Could not locate the game folder.")
	}
	game := filepath.Join(filepath.Dir(self), "Game")
	cmd := exec.Command(filepath.Join(game, "xash3d.exe"), append([]string{"-game", "cstrike"}, os.Args[1:]...)...)
	cmd.Dir = game
	if err = cmd.Start(); err != nil {
		fail("Could not start Counter-Strike. Keep this application beside its Game folder.")
	}
}

func fail(message string) {
	text, _ := syscall.UTF16PtrFromString(message)
	title, _ := syscall.UTF16PtrFromString("Counter-Strike 1.6")
	syscall.NewLazyDLL("user32.dll").NewProc("MessageBoxW").Call(0, uintptr(unsafe.Pointer(text)), uintptr(unsafe.Pointer(title)), 0x10)
	os.Exit(1)
}
