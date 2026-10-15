// the game: GAME_ test markers. UE_LOG is compiled out of Shipping builds, so markers are also printed to stdout
// there; the studio broker captures stdout for `studio run-packaged`.
#pragma once

#include "CoreMinimal.h"
#include <cstdio>

#define GAME_EVENT(Format, ...)                                                    \
	do                                                                             \
	{                                                                              \
		const FString GameEventMsg = FString::Printf(Format, ##__VA_ARGS__);       \
		UE_LOG(LogTemp, Display, TEXT("%s"), *GameEventMsg);                       \
		if (UE_BUILD_SHIPPING)                                                     \
		{                                                                          \
			printf("%s\n", TCHAR_TO_UTF8(*GameEventMsg));                          \
			fflush(stdout);                                                        \
		}                                                                          \
	} while (0)
