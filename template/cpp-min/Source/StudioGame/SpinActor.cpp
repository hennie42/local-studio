#include "SpinActor.h"

ASpinActor::ASpinActor()
{
	PrimaryActorTick.bCanEverTick = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}

void ASpinActor::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	AddActorLocalRotation(FRotator(0.f, DegreesPerSecond * DeltaSeconds, 0.f));
}
